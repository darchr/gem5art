"""This is the gem5 artifact package"""

from gem5art.artifact._artifactdb import ArtifactDB

def getDBConnection() -> ArtifactDB:
    """Returns the database connection

    Eventually, this should likely read from a config file to get the database
    information. However, for now, we'll use mongodb defaults
    """
    return ArtifactDB()
