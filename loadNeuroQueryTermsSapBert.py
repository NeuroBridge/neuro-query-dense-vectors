#!/usr/bin/env python
import argparse
from xml.etree import ElementTree as ET
import config
from transformers import AutoTokenizer, AutoModel
import numpy as np
import torch
from pathlib import Path
from elasticsearch import Elasticsearch
import sys

########################################################################################
#
# This code creates connects to an ElasticSearch instance and creates an index specified 
# with the indexName parameter.  It then reads file in the directory tree specified by
# the inputDir parameter and extracts information. In this case, the file is going to be
# a set of terms used by the NeuroQuery implementation,
# The information is as an input to the Biobert
# sentence embedding module and the resulting vector is passed as part of the input
# from documents in the index. See 
#
#  https://blog.accubits.com/vector-similarity-search-using-elasticsearch/
#
# for some insight into this process.
########################################################################################

def main(args):

   # Extract command line args
   indexName = args.indexName
   termFile = Path(args.termFile)
   shards = args.shards

   # Connect to elasticSearch
   esConn = connectElastic(config.ELASTIC_IP, config.ELASTIC_PORT)

   # Create the index. Note it's currently OK if the index is already there.  We should
   # probably add a command line option to delete the index if it's already there
   createIndex(indexName, shards, esConn)

   insertDataIntoIndex(termFile, indexName, shards, esConn)

def insertDataIntoIndex(termFile, indexName, shards, esConn):
    tokenizer = AutoTokenizer.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")  
    model = AutoModel.from_pretrained("cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
    rowId = 1

    terms = open(termFile, 'r')
    for line in terms:
       cleanLine = line.strip()
       toks = tokenizer.batch_encode_plus([cleanLine], 
                                          padding="max_length", 
                                          max_length=25, 
                                          truncation=True,
                                          return_tensors="pt")
       output = model(**toks)
       cls_rep = output[0][:,0,:]
       print(type(cls_rep))

       embeddingArray = cls_rep.detach().numpy()
       print(type(embeddingArray))
       print(embeddingArray)
       insertBody = {'term_name': cleanLine,
                     'term': cleanLine,
                     'term_vec':  embeddingArray[0],
                     'row_id':  rowId }
       rowId += 1
       esConn.index(index=indexName, body=insertBody)

    print(f"number of rows inserted is {rowId - 1}")
    terms.close()

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

def createIndex(indexName, shards, esConn):
    # Define the index mapping
    indexBodyString = """{
        "mappings": {
            "properties": {
                "term_name": {
                    "type": "text"
                },
                "term": {
                    "type": "text"
                },
                "term_vec": {
                    "type": "dense_vector",
                    "dims": 768
                },
                "row_id": {
                    "type": "long"
                }
            }
        },
        "settings": {
           "number_of_shards": nShards
        }
    }
    """

    indexBody = indexBodyString.replace("nShards", shards)
    print(f"indexBody: {indexBody}")
    try:
        # Create the index if not exists
        if not esConn.indices.exists(indexName):
            # Ignore 400 means to ignore "Index Already Exist" error.
            esConn.indices.create(
                index=indexName, body=indexBody  # ignore=[400, 404]
            )
            print("Created Index: ", indexName)
        else:
            print(f"Index {indexName} already exists")
    except Exception as ex:
        print(str(ex))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Load NeuroQuery terms into a ElasticSearch dense vector")
    parser.add_argument('--termFile',  action="store", 
                        help= "Specify the dir the file containing terms to load")
    parser.add_argument('--indexName',  action="store", 
                        help ="The name of the index in to which to load the data")
    parser.add_argument('--shards',  action="store", 
                        help ="The number of shards in the index.",
                        default =1)

    args = parser.parse_args()

    main(args)
