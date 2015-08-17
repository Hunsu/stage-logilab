from rql import TypeResolverException

from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config


class EntityResource(object):

    def __init__(self, request, cls, attrname, value):
        self.request = request
        self.cls = cls
        self.attrname = attrname
        self.value = value

    @reify
    def rset(self):
        req = self.request.cw_request
        if self.cls is None:
            return req.execute('Any X WHERE X eid %(x)s',
                               {'x': int(self.value)})
        st = self.cls.fetch_rqlst(self.request.cw_cnx.user, ordermethod=None)
        st.add_constant_restriction(st.get_variable('X'), self.attrname,
                                    'x', 'Substitute')
        if self.attrname == 'eid':
            try:
                rset = req.execute(st.as_string(), {'x': int(self.value)})
            except (ValueError, TypeResolverException):
                raise HTTPNotFound()
        else:
            rset = req.execute(st.as_string(), {'x': unicode(self.value)})
        return rset


@view_config(
    route_name='cwentities',
    context=EntityResource,
    request_method='DELETE')
def delete_entity(context, request):
    """a default delete view.
    """
    entity = context.rset.one()
    entity.cw_delete()
    request.response.status_int = 204
    return request.response


def includeme(config):
    # add costum predicates
    config.add_route_predicate('match_is_etype', MatchIsETypePredicate)
    # add routes URLs
    config.add_route(
        'cwentities', '/{etype}/*traverse',
        factory=ETypeResource.from_match('etype'), match_is_etype='etype')
    config.scan(__name__)


@view_config(
    route_name='cwentities',
    context=ETypeResource,
    request_method='GET',
    accept='application/json',
    renderer='json',
)
def get_entities_json(context, request):
    """a default view to render multiple entities
    in JSON format.
    """
    entities = list(context.rset.entities())
    if not len(entities):
        raise HTTPNotFound()
    data = []
    for entity in entities:
        serializer = entity.cw_adapt_to('IJSONSerializable')
        data.append(json.loads(serializer.serialize()))

    request.response.body = json_dumps({'data': data})
    request.response.content_type = 'application/json'
    return request.response
