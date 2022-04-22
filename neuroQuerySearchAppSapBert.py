from flask import Flask, request
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModel
import numpy as np
import torch
from elasticsearch import Elasticsearch
import sys
from timeit import default_timer as timer

# Define the app
app = Flask(__name__)
# Load configs
app.config.from_object('config')
# Set CORS policies
CORS(app)

tokenizer = AutoTokenizer.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
model = AutoModel.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")

def connectElastic(ip, port):
    # Connect to an elasticsearch node with the given ip and port
    esConn = None

    esConn = Elasticsearch([{"host": ip, "port": port}])
    if esConn.ping():
        print("Connected to elasticsearch...")
    else:
        print("Elasticsearch connection error..")
        sys.exit(1)

    return esConn

# Connect to es node
esConn = connectElastic(app.config['ELASTIC_IP'], app.config['ELASTIC_PORT'])

@app.route("/query", methods=["GET"])
def qa():
    print (f"app.config['SEARCH_NUMBER'] is {app.config['SEARCH_NUMBER']}")
    # API to return top_n matched records for a given query
    matches = app.config['SEARCH_NUMBER']
    thresh = app.config['SEARCH_THRESH']

    if request.args.get("max_res"):
        matches = request.args.get("max_res")
        print (f"matches is {matches}")
        matches = int(matches)

    if request.args.get("min_score"):
        thresh = request.args.get("min_score")
        thresh = float(thresh)
        print (f"thresh is {thresh}")

    if request.args.get("query"):
        userQuery = request.args.get("query")
        print (f"userQuery is {userQuery}")

        # Generate embeddings for the input query
        toks = tokenizer.batch_encode_plus([userQuery],
                                           padding="max_length",
                                           max_length=25,
                                           truncation=True,
                                           return_tensors="pt")
        output = model(**toks)
        cls_rep = output[0][:,0,:]

        queryTensor = output[0][:,0,:]
        queryVec = queryTensor.detach().numpy()
        # print (f"queryVec is {queryVec}")

        # Retrieve the semantically similar records for the query
        records = semanticSearch(queryVec[0], app.config['ELASTIC_INDEX_SAP'], thresh, matches)
    else:
        return {"error": "Couldn't process your request"}, 422
    return {"data": records}

def semanticSearch(queryVec, index, thresh, top_n):
    # Retrieve top_n semantically similar records for the given query vector
    if not esConn.indices.exists(index):
        return "No records found"
    s_body = {
        "query": {
            "script_score": {
                "query": {
                    "match_all": {}
                },
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'term_vec') + 1.0",
                    "params": {"query_vector": queryVec}
                }
            }
        }
    }
    # Semantic vector search with cosine similarity
    start = timer()
    result = esConn.search(index=index, body=s_body, size=top_n)
    end = timer()
    searchTime = end - start
    print (end - start)

    total_match = len(result["hits"]["hits"])
    print("Total Matches: ", str(total_match))
    data = []
    data.append({'search_time': searchTime})
    if total_match > 0:
        row_ids = []
        for hit in result["hits"]["hits"]:
            if hit['_score'] > thresh and hit['_source']['row_id'] not in row_ids and len(data) <= top_n:
                print("--\nscore: {} \n variable_id: {} \n description: {}\n--".format(hit["_score"], hit["_source"]['term_name'], hit["_source"]['term']))
                row_ids.append(hit['_source']['row_id'])
                data.append({'term_name': hit["_source"]['term_name'], 'term': hit["_source"]['term'], 'score': hit['_score']})
    return data

if __name__ == '__main__':
    listenPort = app.config['SEARCH_PORT_SAP']
    from waitress import serve
    serve (app, host="0.0.0.0", port=listenPort)
