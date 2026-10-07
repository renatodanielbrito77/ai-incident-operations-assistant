from retrieve_chunks import search_chunks

results = search_chunks("checkout lento ao consultar o serviço de pagamentos")

if not results:
    print("Nenhuma documentação encontrada para a consulta.")
else:
    for result in results:
        print(
            f'{result["score"]:.4f} — '
            f'{result["chunk"]["chunk_id"]}'
        )