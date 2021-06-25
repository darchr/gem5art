import json
from pathlib import Path
from typing import Optional, Iterable, List, Dict, Union, Tuple, Any
from uuid import UUID
import copy

class FileDB:

    """
        An artifact database with a json file backend.
    """

    __json_file: Path
    __uuid_artifact_map: Dict[UUID, Dict[str,str]]
    __hash_uuid_map: Dict[str, List[UUID]]

    def __init__(self, json_file: Union[str, Path]) -> None:
        self.__json_file = Path(json_file)
        self.__uuid_artifact_map, self.__hash_uuid_map = \
            self.__load_from_file(self.__json_file)

    def __load_from_file(self, json_file: Path) -> Tuple[Dict[UUID, Dict[str,str]], Dict[str, List[UUID]]]:
        uuid_mapping: Dict[UUID, Dict[str,str]] = {}
        hash_mapping: Dict[str, List[UUID]] = {}

        with open(json_file, 'r') as f:
            j = json.load(f)
            self.__hash_uuid_map = json.loads(j['hashes'])
            self.__uuid_artifact_map = json.loads(j['artifacts'])
        return uuid_mapping, hash_mapping
    
    def __save_to_file(self, json_file: Path) -> None:
        content = {'artifacts': self.__uuid_artifact_map,
                   'hashes': self.__hash_uuid_map}
        with open(json_file, 'w') as f:
            json.dump(content, f, indent=4)
    
    def has_uuid(self, the_uuid: UUID) -> bool:
        return the_uuid in self.__uuid_artifact_map
    
    def has_hash(self, the_hash: str) -> bool:
        return the_hash in self.__hash_uuid_map
    
    def get_artifact_by_uuid(self, the_uuid: UUID) -> Iterable[Dict[str,str]]:
        if not the_uuid in self.__uuid_artifact_map:
            return
        yield self.__uuid_artifact_map[the_uuid]

    def get_artifact_by_hash(self, the_hash: str) -> Iterable[Dict[str,str]]:
        if not the_hash in self.__hash_uuid_map:
            return
        for the_uuid in self.__hash_uuid_map[the_hash]:
            yield self.__uuid_artifact_map[the_uuid]
    
    def register_file(self, key: UUID, path: Path) -> None:
        pass

    def insert_artifact(self, key: UUID, the_hash: str,
                        the_artifact: Dict[str,Union[str,UUID]]) -> bool:
        """
            Put the artifact to the database.

            Return True if the artifact uuid does not exist in the database prior
            to calling this function; return False otherwise.
        """
        if key in self.__uuid_artifact_map:
            return False
        artifact_copy = copy.deepcopy(the_artifact)
        artifact_copy['_id'] = str(artifact_copy['_id'])
        self.__uuid_artifact_map[key] = artifact_copy # type: ignore
        if not the_hash in self.__hash_uuid_map:
            self.__hash_uuid_map[the_hash] = []
        self.__hash_uuid_map[the_hash].append(key)
        self.__save_to_file(self.__json_file)
        return True
    
    def find_exact(self, attr: Dict[str, str], limit: int)\
                                             -> Iterable[Dict[str, Any]]:
        """
            Return all artifacts such that, for every yielded artifact,
            and for every (k,v) in attr, the attribute `k` of the artifact has
            the value of `v`.
        """
        count = 0
        if count >= limit:
            return
        for artifact in self.__uuid_artifact_map.values():
            # https://docs.python.org/3/library/stdtypes.html#frozenset.issubset
            if attr.items() <= artifact.items():
                yield artifact