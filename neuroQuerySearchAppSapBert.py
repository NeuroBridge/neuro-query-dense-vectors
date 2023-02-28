#!/usr/bin/env python
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModel
import numpy as np
import torch
from elasticsearch import Elasticsearch
import sys
from timeit import default_timer as timer
from neuroquery import fetch_neuroquery_model, NeuroQueryModel
import pandas
import time

# Define the app
app = Flask(__name__)
# Load configs
app.config.from_object('config')
# Set CORS policies
CORS(app)

print("Before tokenizer and model")
tokenizer = AutoTokenizer.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
model = AutoModel.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
print("After tokenizer and model")

def connectElastic(ip, port):
    # Connect to an elasticsearch node with the given ip and port
    returnConn = None

    returnConn = Elasticsearch([{"host": ip, "port": port}])
    while(not returnConn.ping()):
       print("waiting for elasticsearch")
       time.sleep(5)
       returnConn = Elasticsearch([{"host": ip, "port": port}])
#   if returnConn.ping():
#       print("Connected to elasticsearch...")
#   else:
#       print("Elasticsearch connection error..")
#       sys.exit(1)

    return returnConn

# Connect to es node
print(app.config['ELASTIC_IP'])
print(app.config['ELASTIC_PORT'])
esConn = connectElastic(app.config['ELASTIC_IP'], app.config['ELASTIC_PORT'])

# A route added for kubernetes
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify(""), 200

# The route to do a similarity search against the NeuroBridge ontology
@app.route("/neurobridge", methods=["GET"])
def searchNeuroBridge():
    # API to return top_n matched records for a given query

    # Get default values for the number of matches and the search threshold
    print (f"app.config['SEARCH_NUMBER'] is {app.config['SEARCH_NUMBER']}")
    matches = app.config['SEARCH_NUMBER']
    thresh = app.config['SEARCH_THRESH']

    # the number of matches
    if request.args.get("matches"):
        matches = request.args.get("matches")
        matches = int(matches)
        print (f"matches is {matches}")

    # the search threshold
    if request.args.get("thresh"):
        thresh = request.args.get("thresh")
        thresh = float(thresh)
        print (f"thresh is {thresh}")

    # the query to match
    completeResults = []
    if request.args.get("searchTerms"):
        searchTermsFromUser = request.args.get("searchTerms")
        print (f"searchTermsFromUser is {searchTermsFromUser}")

        # The user input can be a "," separated list of terms
        searchTermsList = searchTermsFromUser.split(",")

        for searchTerms in searchTermsList:
           # Generate embeddings for the input query
           toks = tokenizer.batch_encode_plus([searchTerms],
                                              padding="max_length",
                                              max_length=25,
                                              truncation=True,
                                              return_tensors="pt")
           output = model(**toks)
           queryTensor = output[0][:,0,:]
           queryVec = queryTensor.detach().numpy()

           # Retrieve the semantically similar records for the query
           records = semanticSearch(queryVec[0], app.config['NEUROBRIDGE_ELASTIC_INDEX'], thresh, matches)
           recordsWithSearchTerm = {searchTerms: records}
           completeResults.append(recordsWithSearchTerm)
    else:
        return {"error": "Couldn't process your request"}, 422
    return {"data": completeResults}

# The route to do a search using the NeuroQuery API
# Possible ToDo: have this query respect the thresh and matches parameters
@app.route("/neuroquery", methods=["GET"])
def searchNeuroQuery():

    records = []

    # API to return top_n matched records for a given query
    if request.args.get("searchTerms"):
        print("in searchNeuroQuery")
        userQuery = request.args.get("searchTerms")

        encoder = NeuroQueryModel.from_data_dir(fetch_neuroquery_model())
        result = encoder(userQuery)

        # we want to return the title and the pubmed_url
        for index,row in result["similar_documents"].iterrows():
           records.append({'pmid': row['pmid'], 'title': row['title'], 'pubmed_url': row['pubmed_url'], 'similarity': row['similarity']})

    else:
        return {"error": "Couldn't process your request"}, 422
    return {"data": records}

# Query the elastic search index 
def semanticSearch(queryVec, index, thresh, top_n):
    # Retriove top_n semantically similar records for the given query vector
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
    #data.append({'search_time': searchTime})
    if total_match > 0:
        row_ids = []
        for hit in result["hits"]["hits"]:
            if hit['_score'] > thresh and hit['_source']['row_id'] not in row_ids and len(data) <= top_n:
                print("--\nscore: {} \n variable_id: {} \n description: {}\n--".format(hit["_score"], hit["_source"]['term_name'], hit["_source"]['term']))
                row_ids.append(hit['_source']['row_id'])
                data.append({'term_name': hit["_source"]['term_name'], 'term': hit["_source"]['term'], 'score': hit['_score']})
    return data

if __name__ == '__main__':
    listenPort = app.config['SEARCH_PORT']
    listenPort = 8080
    listenMachine = app.config['SEARCH_IP']
    print ("listen port :", listenPort)
    from waitress import serve
    serve (app, host=listenMachine, port=listenPort)
