# Elasticsearch ip and port
#ELASTIC_IP = "host.docker.internal"
ELASTIC_IP = "elasticsearch-master"
#ELASTIC_IP = "0.0.0.0"
ELASTIC_PORT = 9200

# Default threshold and number of search results to return
SEARCH_THRESH = 1.8
SEARCH_NUMBER = 25

# Index to search for NeuroBridge terms. 
NEUROBRIDGE_ELASTIC_INDEX= "neuro_query_docker"

# Port and IP exposed by the server
SEARCH_PORT = 13376
SEARCH_IP = "0.0.0.0"

# The NeuroQuery term file
# local term file
#NEUROQUERY_TERM_FILE = "data-neuroquery_version-1_vocab-neuroquery7547_vocabulary.txt"

# docker based term file
NEUROQUERY_TERM_FILE = "/usr/local/renci/data/data-neuroquery_version-1_vocab-neuroquery7547_vocabulary.txt"

