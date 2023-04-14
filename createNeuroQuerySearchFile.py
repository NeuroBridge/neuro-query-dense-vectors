#!/usr/bin/env python
from transformers import AutoTokenizer, AutoModel
import numpy as np
import torch
from elasticsearch import Elasticsearch
import sys
from timeit import default_timer as timer
from neuroquery import fetch_neuroquery_model, NeuroQueryModel
import pandas
import time
import xml.etree.ElementTree as ET
import argparse
import config
import json

def main(ags):

   # Create an ArgumentParser object
   parser = argparse.ArgumentParser(description='Create a file of precomputed mappings between neurobridge ontology and neuroquery terms')

   # Define the command line arguments
   parser.add_argument('--ontology', help='The ontology file containing the NeuroBridge ontology')
   parser.add_argument('--output',  help='The output file in csv format')

   # Parse the command line arguments
   args = parser.parse_args()

   print("Before tokenizer and model")
   tokenizer = AutoTokenizer.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
   model = AutoModel.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
   print("After tokenizer and model")

   # Connect to es node
   print(config.ELASTIC_IP)
   print(config.ELASTIC_PORT)
   esConn = connectElastic(config.ELASTIC_IP, config.ELASTIC_PORT)

   # Load the XML file
   owl_file_path = args.ontology
   tree = ET.parse(owl_file_path)
   root = tree.getroot()

   # Namespace dictionary for OWL
   owl_ns = {'owl': 'http://www.w3.org/2002/07/owl#',
             'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
             'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}

   # Find all class elements in the OWL file
   class_elements = root.findall(".//owl:Class", namespaces=owl_ns)

   # Loop through the class elements and extract properties
   for class_element in class_elements:
       class_id = class_element.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
       # Print or use the extracted properties as needed
       if (class_id is not None):
          classArray = class_id.split('#')
          concept = classArray[1]
          #print("concept:", concept)
          data = findSearchTermMatches(concept, 10, 1.0, tokenizer, model, esConn)
          print (json.dumps(data, indent=4))

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

def findSearchTermMatches(searchTerm, matches, thresh, tokenizer, model, esConn):
    # API to return top_n matched records for a given query

    # the query to match
    completeResults = []

    # Generate embeddings for the input query
    toks = tokenizer.batch_encode_plus([searchTerm],
                                       padding="max_length",
                                       max_length=25,
                                       truncation=True,
                                       return_tensors="pt")
    output = model(**toks)
    queryTensor = output[0][:,0,:]
    queryVec = queryTensor.detach().numpy()

    # Retrieve the semantically similar records for the query
    records = semanticSearch(queryVec[0], config.NEUROBRIDGE_ELASTIC_INDEX, thresh, matches, esConn)
    recordsWithSearchTerm = {searchTerm: records}
    completeResults.append(recordsWithSearchTerm)
    return {"data": completeResults}

# Query the elastic search index 
def semanticSearch(queryVec, index, thresh, top_n, esConn):
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
    #print (end - start)

    total_match = len(result["hits"]["hits"])
    #print("Total Matches: ", str(total_match))
    data = []
    #data.append({'search_time': searchTime})
    if total_match > 0:
        row_ids = []
        for hit in result["hits"]["hits"]:
            if hit['_score'] > thresh and hit['_source']['row_id'] not in row_ids and len(data) <= top_n:
                #print("--\nscore: {} \n variable_id: {} \n description: {}\n--".format(hit["_score"], hit["_source"]['term_name'], hit["_source"]['term']))
                row_ids.append(hit['_source']['row_id'])
                data.append({'term_name': hit["_source"]['term_name'], 'term': hit["_source"]['term'], 'score': hit['_score']})
    return data

if __name__ == '__main__':
    args = sys.argv[1:]
    main(args)
