from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category

from .exceptions import APIException
from .exceptions import CategoryDoesNotExist
from .exceptions import CategoryNameDuplicate

from .serializers import CategoryCreateSerializer
from .serializers import CategoryReadSerializer
from .serializers import TreeSerializer


class CategoryView(APIView):
    model = Category
    create_serializer = CategoryCreateSerializer
    serializer = TreeSerializer

    def validate_tree(self, siblings, names=[]):
        for s in siblings:
            if s['name'] in names:
                raise CategoryNameDuplicate(
                    detail='Category tree contains duplicate names'
                    )
            names.append(s['name'])
            self.create_serializer(data=s).is_valid(raise_exception=True)
            if s.get('children'):
                self.validate_tree(s['children'], names)

    def create_tree(self, siblings, parent=None):
        for s in siblings:
            data = {
                'name': s['name'],
            }
            if parent:
                data['parent'] = parent
            item = self.model(**data)
            item.save()
            if s.get('children'):
                self.create_tree(s['children'], parent=item)

    def post(self, request):
        self.validate_tree([request.data], names=[])
        self.model.objects.all().delete()
        self.create_tree([request.data])
        root = self.model.objects.filter(parent=None).first()
        return Response(self.serializer(root).data)

    def get(self, request):
        root = self.model.objects.filter(parent=None).first()
        return Response(self.serializer(root).data)

    def delete(self, request):
        self.model.objects.all().delete()
        return Response({})


class CategoryItemView(APIView):
    model = Category
    serializer = CategoryReadSerializer

    def get(self, request, category_id):
        # target item
        try:
            item = self.model.objects.get(pk=category_id)
        except Category.DoesNotExist:
            raise CategoryDoesNotExist(
                detail='{}(id={}) doesn`t exist'.format(
                    self.model.__name__,
                    category_id
                )
            )

        # all its parents
        parents = []
        curr_parrent = item.parent
        while True:
            if curr_parrent:
                parents.append(curr_parrent)
                curr_parrent = curr_parrent.parent
            else:
                break

        # children = all items with item as parent
        children = self.model.objects.filter(parent=item).all()

        # siblings = all items with same parent, besides item on its own
        siblings = self.model.objects.exclude(
            id=item.id
        ).filter(
            parent=item.parent
        ).all()

        data = self.serializer(item).data

        data['parents'] = [self.serializer(p).data for p in parents]
        data['children'] = [self.serializer(c).data for c in children]
        data['siblings'] = [self.serializer(s).data for s in siblings]

        return Response(data)
