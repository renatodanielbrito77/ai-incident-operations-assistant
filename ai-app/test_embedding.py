from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cpu"
)

query = "demora na resposta"

texts = [
    "O checkout apresenta demora ao consultar o serviço de pagamentos.",
    "O usuário alterou a foto do seu perfil"
]

query_embedding = model.encode(query)
text_embeddings = model.encode(texts)

scores = model.similarity(query_embedding, text_embeddings)

for text, score in zip(texts, scores[0]):
    print(f"{float(score):.4f} — {text}")