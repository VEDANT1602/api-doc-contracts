"""Static declared-function documentation contracts; fixture modules are never imported."""
import ast


class RequiresReview(ValueError):
    pass


def annotation(node):
    return ast.unparse(node) if node is not None else None


def signature(node):
    args=node.args;parameters=[]
    positional=args.posonlyargs+args.args
    start_default=len(positional)-len(args.defaults)
    for i,arg in enumerate(positional):
        has=i>=start_default
        parameters.append({'name':arg.arg,'kind':'positional_only' if i<len(args.posonlyargs) else 'positional_or_keyword',
                           'annotation':annotation(arg.annotation),'has_default':has,
                           'default':annotation(args.defaults[i-start_default]) if has else None})
    if args.vararg:
        parameters.append({'name':args.vararg.arg,'kind':'var_positional','annotation':annotation(args.vararg.annotation),
                           'has_default':False,'default':None})
    for arg,default in zip(args.kwonlyargs,args.kw_defaults):
        parameters.append({'name':arg.arg,'kind':'keyword_only','annotation':annotation(arg.annotation),
                           'has_default':default is not None,'default':annotation(default)})
    if args.kwarg:
        parameters.append({'name':args.kwarg.arg,'kind':'var_keyword','annotation':annotation(args.kwarg.annotation),
                           'has_default':False,'default':None})
    return {'async':isinstance(node,ast.AsyncFunctionDef),'parameters':parameters,'return_annotation':annotation(node.returns)}


def extract(source):
    if not isinstance(source,str):raise ValueError('source must be text')
    try:tree=ast.parse(source)
    except SyntaxError as exc:raise RequiresReview('source does not parse') from exc
    def module_execution_nodes(node):
        yield node
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
            # Function-local names are not module exports. A global declaration,
            # however, makes export mutation possible when an unknown call runs.
            if not isinstance(node,ast.Lambda) and any(isinstance(n,ast.Global) and '__all__' in n.names for n in ast.walk(node)):
                raise RequiresReview('function can mutate global exports')
            return
        for child in ast.iter_child_nodes(node):
            yield from module_execution_nodes(child)
    controls=(ast.If,ast.For,ast.AsyncFor,ast.While,ast.Try,ast.With,ast.AsyncWith,ast.Match,ast.ClassDef)
    for statement in tree.body:
        nodes=list(module_execution_nodes(statement))
        if isinstance(statement,controls) and any(isinstance(n,ast.Name) and n.id=='__all__' for n in nodes):
            raise RequiresReview('module control flow may change exports')
        if isinstance(statement,controls) and any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.name.startswith('_') for n in nodes):
            raise RequiresReview('conditional public function requires runtime review')
        if any(isinstance(n,ast.NamedExpr) and isinstance(n.target,ast.Name) and n.target.id=='__all__' for n in nodes):
            raise RequiresReview('assignment expression changes exports')
        if isinstance(statement,ast.Delete) and any(isinstance(n,ast.Name) and n.id=='__all__' for n in nodes):
            raise RequiresReview('export deletion')
    functions={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if len(functions)!=sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for n in tree.body):
        raise RequiresReview('redefined top-level function')
    exports=None
    for node in tree.body:
        if isinstance(node,ast.ImportFrom) and any(a.name=='*' for a in node.names):
            raise RequiresReview('star imports may add unknown public exports')
        target_names=[t.id for t in node.targets if isinstance(t,ast.Name)] if isinstance(node,ast.Assign) else []
        if isinstance(node,ast.Assign) and '__all__' not in target_names and any(
                isinstance(n,ast.Name) and n.id=='__all__' for t in node.targets for n in ast.walk(t)):
            raise RequiresReview('export container mutation')
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute):
            owner=node.value.func.value
            if isinstance(owner,ast.Name) and owner.id=='__all__':
                raise RequiresReview('export method mutation')
        if '__all__' in target_names:
            if exports is not None:raise RequiresReview('multiple export assignments')
            try:value=ast.literal_eval(node.value)
            except (ValueError,TypeError) as exc:raise RequiresReview('dynamic exports require runtime review') from exc
            if not isinstance(value,(list,tuple)) or not all(isinstance(x,str) for x in value) or len(set(value))!=len(value):
                raise RequiresReview('exports must be distinct literal names')
            exports=value
        if isinstance(node,(ast.AugAssign,ast.AnnAssign)) and isinstance(node.target,ast.Name) and node.target.id=='__all__':
            raise RequiresReview('nonliteral export mutation')
    names=exports if exports is not None else sorted(n for n in functions if not n.startswith('_'))
    if any(n not in functions for n in names):raise RequiresReview('export is not a declared top-level function')
    if any(functions[n].decorator_list for n in names):raise RequiresReview('decorator may change the runtime signature')
    return {n:signature(functions[n]) for n in sorted(names)}


def audit(source,documented,signature_aware=True):
    try:actual=extract(source)
    except RequiresReview as exc:
        return {'status':'manual_review','issues':[str(exc)],'declared':None}
    issues=[]
    for name in sorted(set(actual)|set(documented)):
        if name not in actual:issues.append({'name':name,'kind':'documented_function_missing'})
        elif name not in documented:issues.append({'name':name,'kind':'public_function_undocumented'})
        elif signature_aware and actual[name]!=documented[name]:
            issues.append({'name':name,'kind':'declared_signature_drift','documented':documented[name],'actual':actual[name]})
    return {'status':'drift' if issues else 'matched','issues':issues,'declared':actual}


def generate():
    base="""__all__ = ['score', 'configure', 'fetch']

def score(values: list[float], /, threshold: float = 0.5, *, mode: str = 'strict') -> float:
    return threshold

def configure(enabled: bool = True, **options: str) -> None:
    pass

async def fetch(key: str, *, timeout: float = 1.0) -> dict:
    return {}
"""
    cases=[
        ('unchanged',base,'matched'),
        ('renamed_argument',base.replace('threshold: float','cutoff: float').replace('return threshold','return cutoff'),'drift'),
        ('changed_default',base.replace('= 0.5','= 0.75'),'drift'),
        ('removed_default',base.replace('threshold: float = 0.5','threshold: float'),'drift'),
        ('changed_keyword_kind',base.replace(', *, mode',', mode'),'drift'),
        ('changed_annotation',base.replace('timeout: float','timeout: int'),'drift'),
        ('changed_return',base.replace('-> dict','-> list'),'drift'),
        ('changed_async',base.replace('async def fetch','def fetch'),'drift'),
        ('removed_export',base.replace("'score', 'configure', 'fetch'","'score', 'fetch'"),'drift'),
        ('private_helper',base+'\ndef _internal(x):\n    return x\n','matched'),
        ('harmless_comment','# a harmless authored note\n'+base,'matched'),
        ('dynamic_exports',base.replace("['score', 'configure', 'fetch']","build_exports()"),'manual_review'),
        ('decorated_function',base.replace('def configure','@runtime_wrapper\ndef configure'),'manual_review'),
        ('new_public_export',base.replace("'score', 'configure', 'fetch'","'score', 'configure', 'fetch', 'ping'")+'\ndef ping() -> bool:\n    return True\n','drift')]
    return {'base_source':base,'documented_manifest':extract(base),
            'cases':[{'id':cid,'source':source,'expected_status':expected} for cid,source,expected in cases]}


def experiment(data):
    rows=[]
    for case in data['cases']:
        baseline=audit(case['source'],data['documented_manifest'],False)
        checked=audit(case['source'],data['documented_manifest'],True)
        rows.append({'id':case['id'],'expected_status':case['expected_status'],
                     'symbol_only':baseline,'signature_aware':checked,
                     'symbol_only_contract_met':baseline['status']==case['expected_status'],
                     'signature_contract_met':checked['status']==case['expected_status']})
    metrics={'authored_cases':len(rows),'symbol_only_contracts_met':sum(r['symbol_only_contract_met'] for r in rows),
             'signature_aware_contracts_met':sum(r['signature_contract_met'] for r in rows),
             'manual_review_cases':sum(r['expected_status']=='manual_review' for r in rows),
             'executed_fixture_modules':0,'scope':'declared top-level Python function signatures only'}
    report=f"""# Documentation as a checked interface

Topic: developer tooling. Decision: identify documentation that no longer matches a declared public function interface.

A symbol-presence check misses renamed parameters, changed defaults, argument kinds and async behavior. My static checker compares structured signatures from Python ASTs against a versioned documentation manifest. It parses fixture code without importing or executing it. Dynamic exports and decorators produce a manual-review outcome rather than an unjustified match.

Across {len(rows)} authored mutations, symbol-only checking meets {metrics['symbol_only_contracts_met']} contracts and signature-aware checking meets {metrics['signature_aware_contracts_met']}. Two cases require manual review. decisions.json contains every actual and documented signature difference.

These are targeted regression contracts, not documentation quality or LLM accuracy. Module control flow that references exports, conditional public functions, and functions declaring global exports require review. Function-local variables named __all__ are not mistaken for module exports. AST declarations do not prove runtime behavior, side effects, semantic descriptions, API compatibility, or every Python export form. Next, I would integrate this narrow check into a repository that already maintains an explicit public-function documentation manifest and pair it with human semantic review.
"""
    return metrics,rows,None,report
