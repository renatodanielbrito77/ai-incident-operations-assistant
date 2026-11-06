"""CLI V2: não importa embeddings, API ou audit antes de uma operação autorizada."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ai-app'))
from context_rules import evaluate_context
from document_collection import DocumentControl, QdrantBackend, ControlError
from document_policy import DocumentIntegrityError

APPROVED_MANIFEST_SHA256 = '45931762a9a8763cfa2e33fc89e6380c98e7147c546ce94cd99be2562e2352d6'
COLLECTION = 'runbook_chunks_v2_checkout'
VALIDATION_COLLECTIONS = (COLLECTION + '_validation_active_001', COLLECTION + '_validation_transition_001')


def prepare(source):
    """A classificação é explícita, baseada nas decisões recebidas, nunca inferida."""
    root = Path(source)
    manifest_bytes = (root/'manifest.json').read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != APPROVED_MANIFEST_SHA256:
        raise ControlError('Manifesto não corresponde ao lote/classificações aprovados')
    manifest = json.loads(manifest_bytes)
    for record in manifest['files']:
        p = root / record['path']
        if not p.resolve().is_relative_to(root.resolve()):
            raise ControlError('Manifesto aponta para fora da origem')
        b = p.read_bytes()
        if len(b) != record['bytes'] or hashlib.sha256(b).hexdigest() != record['sha256']:
            raise ControlError('Origem diverge do manifesto')
    specs = [('RB-V2-001', '1.0', 'active', '2026-10-20'),
             ('RB-V2-002', '0.7', 'unconfirmed', None)]
    result = []
    for doc, version, status, reviewed in specs:
        p = root/'procedures'/f'{doc}.md'
        content = p.read_text()
        # Nenhum texto é removido: preâmbulo e seções com quebras originais.
        starts = [0] + [m.start() for m in re.finditer(r'^## ', content, re.M)] + [len(content)]
        for index, (a,b) in enumerate(zip(starts, starts[1:]), 1):
            text = content[a:b]
            section = text.splitlines()[0][3:] if text.startswith('## ') else 'Metadados recebidos'
            result.append(dict(chunk_id=f'{doc}@{version}:{index:02}', document_id=doc,
                document_version=version, document_status=status, review_date=reviewed,
                classification_revision=1, classified_by='Marina', source=str(p.resolve()),
                section=section, subsection=None, content=text))
        assert ''.join(c['content'] for c in result if c['document_id']==doc)==content
    return result


def validate_run(args, result_dir):
    chunks = prepare(args.source_dir)
    # Vetores controlados testam filtro/ranking, não qualidade de recuperação.
    # Inelegíveis recebem score 1, ativos menor score, ainda acima de 0,50.
    vectors = [[0.8, 0.6] if c['document_status']=='active' else [1.0, 0.0] for c in chunks]
    report = {'scope':'filter/classification validation, not semantic retrieval or baseline', 'collections':[]}
    for name in VALIDATION_COLLECTIONS:
        with DocumentControl(Path(args.state_dir)/name, name, args.qdrant_url, QdrantBackend(args.qdrant_url, name)) as ctl:
            ctl.load(chunks, vectors, 2)
            results = ctl.search([1.0,0.0])
            assert results and all(r['chunk']['document_id']=='RB-V2-001' for r in results)
            limits = ctl.limits('RB-V2-001','1.0')
            assert limits and not ctl.limits('RB-V2-002','0.7')
            incident = json.loads((Path(args.source_dir)/'incidents/INC-V2-001.json').read_text())
            decision = evaluate_context(results, limits)
            context = dict(audit_event_id='validation-only-no-persisted-audit-event',
                incident=incident['incident'], monitoring=incident['monitoring'], logs=incident['logs'],
                historical_incidents=[], historical_incident_matches=[], documentation=results,
                document_limits=limits, documentation_status='retrieved', **decision)
            package = ctl.package(context)
            assert package.evidence.documentation[0].chunk.document_status=='active'
            row = dict(collection=name, search_ids=[r['chunk']['chunk_id'] for r in results],
                       limit_ids=[c['chunk_id'] for c in limits], package=package.model_dump(),
                       audit_note='synthetic validation marker; no audit event generated/persisted')
            if name == VALIDATION_COLLECTIONS[1]:
                ctl.reclassify('RB-V2-001','1.0','deprecated','technical-validation-only')
                assert not ctl.search([1.0,0.0]) and not ctl.limits('RB-V2-001','1.0')
                try:
                    ctl.package(context)
                except DocumentIntegrityError:
                    row['old_context_rejected']=True
                else:
                    raise AssertionError('Old context accepted')
                no_docs = {**context, 'documentation':[], 'document_limits':[],
                           'documentation_status':'no_matches', **evaluate_context([],[])}
                assert ctl.package(no_docs).status=='not_eligible'
                row['after_transition']='not_eligible; no active documents'
            report['collections'].append(row)
            (result_dir/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['load','validate','reclassify','reconcile'])
    parser.add_argument('--collection',default=COLLECTION)
    parser.add_argument('--qdrant-url',default='http://vector-db:6333')
    parser.add_argument('--state-dir',required=True)
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--source-dir')
    parser.add_argument('--document-id')
    parser.add_argument('--version')
    parser.add_argument('--status',choices=['active','deprecated','unconfirmed'])
    parser.add_argument('--classified-by')
    args=parser.parse_args(argv)
    out=Path(args.output_dir)
    # Destino novo é obrigatório. Sem repetição/sobrescrita automática.
    try:
        out.mkdir(parents=True,exist_ok=False)
    except OSError as exc:
        print(f'ERRO: destino de resultados indisponível: {exc}')
        return 2
    (out/'request.json').write_text(json.dumps(vars(args),indent=2))
    try:
        if args.operation in ('load','validate') and not args.source_dir:
            raise ControlError('--source-dir é obrigatório')
        if args.operation=='validate':
            result=validate_run(args,out)
        else:
            with DocumentControl(args.state_dir,args.collection,args.qdrant_url,QdrantBackend(args.qdrant_url,args.collection)) as ctl:
                if args.operation=='load':
                    chunks=prepare(args.source_dir)
                    from sentence_transformers import SentenceTransformer
                    model=SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',device='cpu',local_files_only=True)
                    for c in chunks:
                        count=len(model.tokenizer(c['content'],truncation=False)['input_ids'])
                        if count>model.max_seq_length:
                            raise ControlError(f"Chunk excede limite; não truncar: {c['chunk_id']}")
                    vectors=model.encode([c['content'] for c in chunks]).tolist()
                    ctl.load(chunks,vectors,len(vectors[0]))
                elif args.operation=='reclassify':
                    if not all((args.document_id,args.version,args.status,args.classified_by)):
                        raise ControlError('Reclassificação exige documento, versão, status e responsável')
                    ctl.reclassify(args.document_id,args.version,args.status,args.classified_by)
                else:
                    ctl.reconcile()
                result={'operation':args.operation,'state':ctl.read()[0]}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print('CONCLUÍDO — controle documental; nenhuma geração ou avaliação de participantes')
        return 0
    except Exception as exc:
        (out/'error.json').write_text(json.dumps(dict(type=type(exc).__name__,message=str(exc)),ensure_ascii=False,indent=2))
        print(f'ERRO OPERACIONAL — {type(exc).__name__}: {exc}')
        return 2


if __name__=='__main__':
    raise SystemExit(main())
