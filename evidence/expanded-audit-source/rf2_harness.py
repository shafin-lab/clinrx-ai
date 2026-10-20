"""Isolated synthetic contract harness. No application, persistence or network imports."""
import calendar
import hashlib
import itertools
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CONTRACT = 'rf2-harness/v1-proposal.2'
RESOLVER = 'rf2-isolated-resolver/1.0.0'
SCHEMA_BYTES = Path(__file__).with_name('schema.json').read_bytes()
SCHEMA = json.loads(SCHEMA_BYTES)
SCHEMA_DIGEST = hashlib.sha256(SCHEMA_BYTES).hexdigest()
REGISTRY_TYPES = tuple(sorted(('component_aliases', 'quantity_equivalence', 'drain_lifecycle', 'independent_components')))
SUPPORTED = ('clinrx.synthetic.fluid-collections', '0.1.0-proposal.1', 'clinrx.fluid-collection-profile/v1-proposal.1')
MAX_BYTES = 4 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def registry_digest(value):
    return digest({k: v for k, v in value.items() if k != 'digest'})


class Invalid(Exception):
    def __init__(self, reason='SCHEMA_REJECTED', path='$'):
        self.reason, self.path = reason, path


class Limit(Invalid):
    pass


def instant(text):
    """Exact seconds since epoch, including all supplied fractional digits."""
    m = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})', text)
    if not m:
        raise Invalid()
    try:
        if m[3] != 'Z' and (int(m[3][1:3]) > 23 or int(m[3][4:6]) > 59):
            raise ValueError()
        dt = datetime.fromisoformat(m[1] + m[3].replace('Z', '+00:00'))
        seconds = calendar.timegm(dt.astimezone(timezone.utc).timetuple())
        with localcontext() as ctx:
            ctx.prec = 1024
            return Decimal(seconds) + Decimal(m[2] or '0')
    except (ValueError, OverflowError):
        raise Invalid() from None


def zone_check(text, name):
    try:
        # Fraction does not affect local offset correspondence; retain exact value in instant().
        base = re.sub(r'\.\d+(?=Z|[+-]\d\d:\d\d$)', '', text)
        dt = datetime.fromisoformat(base.replace('Z', '+00:00'))
        local = dt.astimezone(ZoneInfo(name))
        if local.replace(tzinfo=None) != dt.replace(tzinfo=None) or local.utcoffset() != dt.utcoffset():
            raise Invalid()
    except (ValueError, OverflowError, ZoneInfoNotFoundError):
        raise Invalid() from None


def preflight(value, depth=0):
    if depth > 32:
        raise Limit('INPUT_LIMIT')
    if isinstance(value, str):
        if len(value) > 512:
            raise Invalid()
    elif type(value) is list:
        if len(value) > 256:
            raise Limit('INPUT_LIMIT')
        for item in value:
            preflight(item, depth + 1)
    elif type(value) is dict:
        for k, v in value.items():
            if type(k) is not str:
                raise Invalid()
            preflight(k, depth + 1)
            preflight(v, depth + 1)
    elif value is not None and type(value) not in (bool, int):
        raise Invalid()


def validate_shape(value, schema, path='$'):
    """Interpret only the small, published closed schema vocabulary."""
    if '$ref' in schema:
        return validate_shape(value, SCHEMA['definitions'][schema['$ref']], path)
    if 'anyOf' in schema:
        for choice in schema['anyOf']:
            try:
                validate_shape(value, choice, path)
                return
            except Invalid:
                pass
        raise Invalid(path=path)
    if 'enum' in schema and not any(type(value) is type(x) and value == x for x in schema['enum']):
        raise Invalid('UNSUPPORTED_UNIT' if path.endswith('.unit') else 'SCHEMA_REJECTED', path)
    typ = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool, 'null': type(None)}
    if typ and type(value) is not types[typ]:
        raise Invalid(path=path)
    if typ == 'object':
        props = schema.get('properties')
        if props is not None:
            if set(value) != set(schema['required']):
                raise Invalid(path=path)
            for k in props:
                validate_shape(value[k], props[k], path + '.' + k)
    if typ == 'array':
        if len(value) > schema.get('maxItems', 256):
            raise Limit('INPUT_LIMIT', path)
        if len(value) < schema.get('minItems', 0):
            raise Invalid(path=path)
        for v in value:
            validate_shape(v, schema['items'], path + '[]')
    if typ == 'string':
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 512):
            raise Invalid(path=path)
        if 'pattern' in schema and re.fullmatch(schema['pattern'], value) is None:
            raise Invalid(path=path)
        if schema.get('format') == 'instant':
            instant(value)
        if schema.get('format') == 'uuid':
            try:
                UUID(value)
            except ValueError:
                raise Invalid(path=path) from None
    if typ == 'integer' and value < schema.get('minimum', value):
        raise Invalid(path=path)


def unique_refs(items):
    encoded = [canonical(x) for x in items]
    if len(encoded) != len(set(encoded)):
        raise Invalid()


def validate(run):
    preflight(run)
    validate_shape(run, SCHEMA['run'])
    if instant(run['period']['start']) >= instant(run['period']['end']):
        raise Invalid('INVALID_INTERVAL_STRUCTURE')
    for v in ('start', 'end'):
        zone_check(run['period'][v], run['period']['display_timezone'])
    for wrapper in run['records']:
        e = wrapper['envelope']
        q, t = e['quantity'], e['time']
        if (q['amount'] is None) != (q['unit'] is None):
            raise Invalid()
        if t['kind'] == 'interval':
            if t['start'] is None or t['end'] is None or t['at'] is not None or instant(t['start']) >= instant(t['end']):
                raise Invalid('INVALID_INTERVAL_STRUCTURE')
            for k in ('start', 'end'):
                zone_check(t[k], t['display_timezone'])
        else:
            if t['at'] is None or t['start'] is not None or t['end'] is not None:
                raise Invalid('INVALID_INTERVAL_STRUCTURE')
            zone_check(t['at'], t['display_timezone'])
        if e['category'] == 'output_drain':
            if e['drain_key'] is None or e['drain_name'] is None:
                raise Invalid()
        elif e['drain_key'] is not None or e['drain_name'] is not None:
            raise Invalid()
        if e['classification'] == 'collection' and e['summary_members'] is not None:
            raise Invalid()
        unique_refs(e['summary_members'] or [])
        unique_refs(e['equivalence'])
    for r in run['registries']:
        validate_shape(r['content'], SCHEMA['definitions'][r['registry_type']], '$.registry.content')
        # Digest mismatches are semantic registry failures, not malformed JSON.


def scope(value):
    s = value['scope']
    return (s['repository'], s['patient_id'], s['encounter_id'], value['issuer']['namespace'], value['issuer']['id'], value['identity_namespace'])


def expected_scope(run):
    s = run['expected_scope']
    return (s['repository'], s['patient_id'], s['encounter_id'], s['issuer']['namespace'], s['issuer']['id'], s['identity_namespace'])


def supports(e):
    return (e['producer']['id'], e['producer']['version'], e['profile']) == SUPPORTED


def bounds(e):
    t = e['time']
    return (instant(t['at']), instant(t['at'])) if t['kind'] == 'point' else (instant(t['start']), instant(t['end']))


def overlaps(a, b):
    x, y = bounds(a)
    c, d = bounds(b)
    if a['time']['kind'] == b['time']['kind'] == 'point':
        return x == c
    if a['time']['kind'] == 'point':
        return c <= x < d
    if b['time']['kind'] == 'point':
        return x <= c < y
    return max(x, c) < min(y, d)


class Union:
    def __init__(self):
        self.parent = {}

    def root(self, a):
        self.parent.setdefault(a, a)
        if self.parent[a] != a:
            self.parent[a] = self.root(self.parent[a])
        return self.parent[a]

    def join(self, a, b):
        x, y = self.root(a), self.root(b)
        if x != y:
            self.parent[max(x, y)] = min(x, y)


def select_registries(run, withheld):
    selected, diagnostics = {}, []
    rows = [r for r in run['registries'] if r['knowledge_sequence'] <= run['cutoff']]
    if any(scope(r) != expected_scope(run) for r in rows):
        withheld.add('SCOPE_UNBOUNDED')
    for typ in REGISTRY_TYPES:
        family = [r for r in rows if r['registry_type'] == typ and scope(r) == expected_scope(run)]
        by = defaultdict(list)
        for r in family:
            by[r['version']].append(r)
        invalid = not family
        for rs in by.values():
            if len({canonical(r) for r in rs}) != 1 or any(r['digest'] != registry_digest(r) for r in rs):
                invalid = True
        distinct = {k: v[0] for k, v in by.items()}
        used, children = set(), defaultdict(list)
        for version, r in distinct.items():
            p = r['supersedes']
            if p:
                old = distinct.get(p['version'])
                if old is None or p['registry_type'] != typ or old['digest'] != p['digest'] or old['knowledge_sequence'] > r['knowledge_sequence']:
                    invalid = True
                used.add(p['version'])
                children[p['version']].append(version)
        roots = [v for v, r in distinct.items() if r['supersedes'] is None]
        terminals = sorted(set(distinct) - used)
        if len(roots) != 1 or len(terminals) != 1 or any(len(v) > 1 for v in children.values()):
            invalid = True
        if not invalid:
            seen, current = set(), terminals[0]
            while current is not None:
                if current in seen:
                    invalid = True
                    break
                seen.add(current)
                p = distinct[current]['supersedes']
                current = p['version'] if p else None
            if seen != set(distinct):
                invalid = True
        if invalid:
            withheld.add('REGISTRY_UNAVAILABLE' if not family else 'REGISTRY_CONFLICT')
            diagnostics.append({'registry_type': typ, 'status': 'unavailable'})
            continue
        terminal = distinct[terminals[0]]
        diagnostics.append({'registry_type': typ, 'version': terminal['version'], 'digest': terminal['digest'], 'available_at': terminal['available_at'], 'knowledge_sequence': terminal['knowledge_sequence']})
        if run['clinical_as_of'] is not None and instant(terminal['available_at']) > instant(run['clinical_as_of']):
            withheld.add('REGISTRY_TERMINAL_AFTER_AS_OF')
            continue
        selected[typ] = terminal['content']['entries']
    return selected, diagnostics


def resolve(run):
    withheld = set()
    if not run['input_complete']:
        withheld.add('INPUT_INCOMPLETE')
    regs, pins = select_registries(run, withheld)
    wrappers = [w for w in run['records'] if w['knowledge_sequence'] <= run['cutoff']]
    if any(scope(w['envelope']) != expected_scope(run) for w in wrappers):
        withheld.add('SCOPE_UNBOUNDED')
    # Exact canonical replay collapse; knowledge history is retained without input indices.
    nodes = {}
    for w in wrappers:
        e = w['envelope']
        h = digest(e)
        n = nodes.setdefault(h, {'e': e, 'sequences': set(), 'reasons': set(), 'groups': set()})
        n['sequences'].add(w['knowledge_sequence'])
    aliases = defaultdict(set)
    alias_quantities = defaultdict(set)
    for a in regs.get('component_aliases', []):
        aliases[(a['collection_key'], a['alias'])].add(a['canonical'])
        alias_quantities[(a['collection_key'], a['alias'])].add(a['quantity_key'])

    def component(collection, key):
        seen = set()
        while (collection, key) in aliases:
            if key in seen or len(aliases[(collection, key)]) != 1:
                raise ValueError('alias conflict')
            seen.add(key)
            key = next(iter(aliases[(collection, key)]))
        return key

    for (collection, key) in aliases:
        try:
            component(collection, key)
            if len(alias_quantities[(collection, key)]) != 1:
                raise ValueError()
        except ValueError:
            # Alias registry scope is global; no unsupported assumption about unaffected input.
            withheld.add('ALIAS_UNRESOLVED')
    for h, n in nodes.items():
        e = n['e']
        try:
            c = component(e['collection_key'], e['component_key'])
        except ValueError:
            c = e['component_key']
            n['reasons'].add('ALIAS_UNRESOLVED')
        n['identity'] = (*scope(e), e['collection_key'], c, e['revision'])
        alias_q = alias_quantities.get((e['collection_key'], e['component_key']))
        if alias_q and e['quantity_key'] not in alias_q:
            n['reasons'].add('ALIAS_UNRESOLVED')
        if not supports(e):
            n['reasons'].add('UNSUPPORTED_PROFILE')

    edges = set()
    conflict = Union()

    def edge(a, b, typ, reason=None):
        if a == b:
            return
        x, y = sorted((a, b))
        edges.add((x, y, typ, reason or ''))
        if typ == 'CONFLICT':
            conflict.join(x, y)
            nodes[a]['reasons'].add(reason)
            nodes[b]['reasons'].add(reason)

    def family_conflict(ids, reason):
        ids = sorted(ids)
        for h in ids:
            nodes[h]['reasons'].add(reason)
        for a, b in itertools.combinations(ids, 2):
            edge(a, b, 'CONFLICT', reason)

    families = defaultdict(list)
    for h, n in nodes.items():
        families[n['identity'][:-1]].append(h)
    selected = set()
    for fam, ids in sorted(families.items()):
        revisions = defaultdict(list)
        for h in ids:
            revisions[nodes[h]['e']['revision']].append(h)
        reasons, parents, children = set(), {}, defaultdict(list)
        if any(len(v) > 1 for v in revisions.values()):
            reasons.add('SAME_REVISION_CONFLICT')
        for h in ids:
            e = nodes[h]['e']
            p = e['supersedes']
            if p:
                try:
                    pc = component(p['collection_key'], p['component_key'])
                except ValueError:
                    pc = p['component_key']
                    reasons.add('ALIAS_UNRESOLVED')
                if (p['identity_namespace'], p['collection_key'], pc) != (e['identity_namespace'], e['collection_key'], fam[-1]):
                    reasons.add('DEPENDENCY_MISSING')
                ps = revisions.get(p['revision'], [])
                if len(ps) != 1:
                    reasons.add('DEPENDENCY_MISSING')
                else:
                    parent = ps[0]
                    if min(nodes[parent]['sequences']) > min(nodes[h]['sequences']):
                        reasons.add('DEPENDENCY_MISSING')
                    parents[h] = parent
                    children[parent].append(h)
                    edge(parent, h, 'LINEAGE')
        if any(len(v) > 1 for v in children.values()):
            reasons.add('REVISION_BRANCH')
        for h in ids:
            seen, current = set(), h
            while current in parents:
                if current in seen:
                    reasons.add('REVISION_CYCLE')
                    break
                seen.add(current)
                current = parents[current]
        roots = set(ids) - set(parents)
        terminals = set(ids) - set(children)
        if len(roots) != 1 or len(terminals) != 1:
            reasons.add('REVISION_BRANCH')
        if reasons:
            for r in sorted(reasons):
                family_conflict(ids, r)
            selected.update(ids)  # Retain unresolved representations in other conflict analysis.
            if 'DEPENDENCY_MISSING' in reasons:
                withheld.add('DEPENDENCY_MISSING')
            for h in ids:
                nodes[h]['applicable'] = None
        else:
            terminal = next(iter(terminals))
            selected.add(terminal)
            for h in ids:
                nodes[h]['applicable'] = terminal
                if h != terminal:
                    nodes[h]['reasons'].add('SUPERSEDED_AT_CUTOFF')
            if nodes[terminal]['e']['status'] != 'recorded':
                nodes[terminal]['reasons'].add('TERMINAL_NOT_RECORDED')

    quantities = Union()
    for n in nodes.values():
        quantities.root(n['e']['quantity_key'])
    for q in regs.get('quantity_equivalence', []):
        quantities.join(q['left_quantity_key'], q['right_quantity_key'])
    for h in selected:
        e = nodes[h]['e']
        for q in e['equivalence']:
            quantities.join(e['quantity_key'], q['quantity_key'])
    all_quantities = {n['e']['quantity_key'] for n in nodes.values()}
    for h in selected:
        for q in nodes[h]['e']['equivalence']:
            if q['quantity_key'] not in all_quantities:
                withheld.add('DEPENDENCY_MISSING')
    independence = set()
    for entry in regs.get('independent_components', []):
        parts = []
        for c in entry['components']:
            try:
                comp = component(entry['collection_key'], c['component_key'])
            except ValueError:
                withheld.add('ALIAS_UNRESOLVED')
                continue
            parts.append((comp, c['quantity_key']))
        if len({x[0] for x in parts}) != len(parts) or len({x[1] for x in parts}) != len(parts):
            withheld.add('REGISTRY_CONFLICT')
        for a, b in itertools.combinations(parts, 2):
            if quantities.root(a[1]) == quantities.root(b[1]):
                for h in selected:
                    if nodes[h]['e']['quantity_key'] in (a[1], b[1]):
                        nodes[h]['reasons'].add('REGISTRY_CONFLICT')
            independence.add((entry['collection_key'], *sorted((a, b))))

    drains = defaultdict(list)
    for d in regs.get('drain_lifecycle', []):
        drains[d['drain_key']].append(d)
    for key, rows in drains.items():
        d = rows[0]
        if len(rows) != 1 or (d['active_until'] is not None and instant(d['active_until']) <= instant(d['active_from'])):
            withheld.add('REGISTRY_CONFLICT')
        if d['replaces'] is not None:
            old = drains.get(d['replaces'], [])
            if len(old) != 1 or old[0]['active_until'] is None or instant(old[0]['active_until']) > instant(d['active_from']):
                withheld.add('REGISTRY_CONFLICT')
        seen, k = set(), key
        while k in drains and len(drains[k]) == 1 and drains[k][0]['replaces'] is not None:
            if k in seen:
                withheld.add('REGISTRY_CONFLICT')
                break
            seen.add(k)
            k = drains[k][0]['replaces']
    for h in selected:
        n, e = nodes[h], nodes[h]['e']
        if e['category'] == 'output_drain':
            ds = drains.get(e['drain_key'], [])
            if len(ds) != 1:
                n['reasons'].add('DRAIN_LIFECYCLE')
            else:
                d = ds[0]
                a, b = bounds(e)
                ok = a >= instant(d['active_from'])
                if d['active_until'] is not None:
                    end = instant(d['active_until'])
                    ok = ok and (b <= end if e['time']['kind'] == 'interval' else a < end)
                if not ok:
                    n['reasons'].add('DRAIN_LIFECYCLE')

    # Known summary membership is a typed relation, never a collection overlap edge.
    collections = sorted(h for h in selected if nodes[h]['e']['classification'] == 'collection')
    q_members = defaultdict(list)
    for h in collections:
        q_members[quantities.root(nodes[h]['e']['quantity_key'])].append(h)
    for h in selected:
        e = nodes[h]['e']
        if e['classification'] == 'summary':
            nodes[h]['reasons'].add('SUMMARY')
            if e['summary_members'] is None:
                withheld.add('SCOPE_UNBOUNDED')
            else:
                for q in e['summary_members']:
                    members = q_members.get(quantities.root(q['quantity_key']), [])
                    if not members:
                        withheld.add('DEPENDENCY_MISSING')
                    for member in members:
                        edge(h, member, 'SUMMARY_MEMBER')

    for a, b in itertools.combinations(collections, 2):
        ea, eb = nodes[a]['e'], nodes[b]['e']
        if quantities.root(ea['quantity_key']) == quantities.root(eb['quantity_key']):
            edge(a, b, 'EQUIVALENT_VOLUME')
            edge(a, b, 'CONFLICT', 'DUPLICATE_UNRESOLVED')
        ca, cb = nodes[a]['identity'][-2], nodes[b]['identity'][-2]
        if ea['collection_key'] == eb['collection_key'] and ca != cb:
            pair = (ea['collection_key'], *sorted(((ca, ea['quantity_key']), (cb, eb['quantity_key']))))
            if pair not in independence:
                edge(a, b, 'CONFLICT', 'COMPONENT_INDEPENDENCE_UNRESOLVED')
            else:
                edge(a, b, 'INDEPENDENCE')
        # Independent drain instances have distinct source_instance keys.
        stream_a = (scope(ea), ea['category'], ca, ea['drain_key'] if ea['category'] == 'output_drain' else 'unspecified-source')
        stream_b = (scope(eb), eb['category'], cb, eb['drain_key'] if eb['category'] == 'output_drain' else 'unspecified-source')
        if ea['collection_key'] != eb['collection_key'] and stream_a == stream_b and overlaps(ea, eb):
            edge(a, b, 'CONFLICT', 'SAME_STREAM_OVERLAP')
    # Include noncollection alternate bodies of a conflicting same-component family;
    # no arbitrary category/classification representation is preferred.
    conflict_members = defaultdict(list)
    for h in nodes:
        if h in conflict.parent:
            conflict_members[conflict.root(h)].append(h)
    groups = []
    for members in sorted(conflict_members.values(), key=lambda v: sorted(v)):
        members = sorted(members)
        reasons = sorted({r for h in members for r in nodes[h]['reasons'] if r in {e[3] for e in edges if e[2] == 'CONFLICT'}})
        typed = [{'members': [a, b], 'type': t, 'reason': r or None} for a, b, t, r in sorted(edges) if a in members and b in members and t in ('CONFLICT', 'EQUIVALENT_VOLUME', 'LINEAGE')]
        identity_members = [{'identity': list(nodes[h]['identity']), 'digest': h} for h in members]
        gid = digest({'members': identity_members, 'edges': typed, 'reasons': reasons})
        groups.append({'id': gid, 'members': members, 'reason_codes': reasons, 'typed_edges': typed})
        for h in members:
            nodes[h]['groups'].add(gid)
            nodes[h]['reasons'].update(reasons)

    begin, end = instant(run['period']['start']), instant(run['period']['end'])
    for h, n in nodes.items():
        e, reasons = n['e'], n['reasons']
        if not e['actual_recorded']:
            reasons.add('NON_ACTUAL')
        if e['quantity']['amount'] is None:
            reasons.add('MISSING_QUANTITY')
        if e['classification'] == 'summary':
            reasons.add('SUMMARY')
        if e['category'] == 'output_crrt_effluent':
            reasons.add('EFFLUENT')
        a, b = bounds(e)
        contained = begin <= a < end if e['time']['kind'] == 'point' else begin <= a < b <= end
        if not contained:
            reasons.add('CROSSING_PERIOD' if a < end and b > begin else 'OUTSIDE_PERIOD')
        if run['clinical_as_of'] is not None:
            if e['available_at'] is None:
                reasons.add('AVAILABILITY_UNRESOLVED')
            elif instant(e['available_at']) > instant(run['clinical_as_of']):
                reasons.add('AFTER_CLINICAL_AS_OF')
    decisions = []
    for h, n in sorted(nodes.items(), key=lambda item: (item[1]['identity'], item[0])):
        reasons = sorted(n['reasons'])
        decision = 'exclude' if reasons else 'unresolved' if withheld else 'candidate_include'
        decisions.append({'identity': list(n['identity']), 'envelope_digest': h, 'knowledge_sequences': sorted(n['sequences']), 'decision': decision, 'reason_codes': reasons or sorted(withheld) or ['CANDIDATE_RULES_SATISFIED'], 'applicable_revision': nodes[n['applicable']]['identity'] if n.get('applicable') else None, 'conflict_group_ids': sorted(n['groups']), 'registry_pins': pins})
    return {'run_status': 'withheld' if withheld else 'evaluated', 'run_reasons': sorted(withheld), 'decisions': decisions, 'conflict_groups': sorted(groups, key=lambda g: g['id']), 'relationships': [{'members': [a, b], 'type': t, 'reason': r or None} for a, b, t, r in sorted(edges)], 'selected_registries': pins}


def evaluate(raw):
    """Accept UTF-8 JSON bytes only; return decisions, never numerical eligibility."""
    output = {'contract_version': CONTRACT, 'schema_digest': SCHEMA_DIGEST, 'resolver_version': RESOLVER, 'synthetic_only': True, 'input_digest': None, 'requested_scope': None, 'period': None, 'cutoff': None, 'clinical_as_of': None, 'selected_registries': [], 'run_status': 'rejected', 'run_reasons': [], 'decisions': [], 'conflict_groups': [], 'relationships': [], 'completeness': 'unresolved', 'numerical_eligibility_active': False}
    try:
        if type(raw) is not bytes:
            raise Invalid()
        if len(raw) > MAX_BYTES:
            raise Limit('INPUT_LIMIT')
        def pairs(items):
            result = {}
            for k, v in items:
                if k in result:
                    raise Invalid()
                result[k] = v
            return result
        def bad_number(_):
            raise Invalid()
        run = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_float=bad_number, parse_constant=bad_number)
        preflight(run)
        output['input_digest'] = digest(run)
        validate(run)
        output.update(requested_scope=run['expected_scope'], period=run['period'], cutoff=run['cutoff'], clinical_as_of=run['clinical_as_of'])
        output.update(resolve(run))
    except Limit as exc:
        output.update(run_status='withheld', run_reasons=[exc.reason])
    except (Invalid, ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
        output.update(run_status='rejected', run_reasons=[exc.reason if isinstance(exc, Invalid) else 'SCHEMA_REJECTED'], decisions=[], conflict_groups=[], relationships=[])
    return output


def main():
    import sys
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    sys.stdout.buffer.write(canonical(evaluate(raw)) + b'\n')


if __name__ == '__main__':
    main()
