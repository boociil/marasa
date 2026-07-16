from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import PointStruct
from langchain_chroma import Chroma
import uuid

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


async def load_data(vectorstore_Chroma: Chroma, collection_name) :
    BATCH = 1000
    offset = 0

    qdrant  = QdrantClient(
        url="http://10.76.0.2:6333",
        api_key=os.getenv('QDRANT_API_KEY', '')
    )

    collection =  vectorstore_Chroma._collection
    while True:
        data = collection.get(
            limit=BATCH,
            offset=offset,
            include=[
                "documents",
                "metadatas",
                "embeddings"
            ]
        )

        if not data["ids"]:
            break


        total = collection.count()

        embedding_size = len(data["embeddings"][0])

        if not qdrant.collection_exists(collection_name):
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_size,
                    distance=Distance.COSINE
                )
            )

        points = []

        for chroma_id, embedding, document, metadata  in zip(
            data["ids"],
            data["embeddings"],
            data["documents"],
            data["metadatas"]
        ):
            payload = dict(metadata or {})

            # simpan id lama
            payload["chroma_id"] = chroma_id

            # simpan document
            payload["document"] = document

            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, chroma_id)),
                    vector=embedding,
                    payload=payload,
                )
            )

        if points:
            qdrant.upsert(
                collection_name=collection_name,
                points=points,
                wait=True,
            )
        
        print(
            f"Migrated {min(offset + BATCH, total)}/{total}"
        )

        offset += BATCH
    print("Done.")

        