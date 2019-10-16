"""This is the gem5 artifact package"""

import gem5art.artifact.artifactdb

def getDBConnection():
    """Returns the database connection

    Eventually, this should likely read from a config file to get the database
    information. However, for now, we'll use mongodb defaults
    """
    return artifactdb.ArtifactDB()
