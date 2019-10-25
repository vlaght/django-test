from collections import OrderedDict

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework import serializers

from .models import Category
# Create your views here.


class CategoryDoesNotExist(APIException):
    status_code = 404


class CategoryNameDuplicate(APIException):
    status_code = 409


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CategoryCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    children = RecursiveField(many=True, required=False)

    class Meta:
        model = Category
        fields = ('name', 'children')
        read_only_fields = ('name', 'children')

    def validate(self, data):
        if hasattr(self, 'initial_data'):
            unknown_keys = set(self.initial_data.keys()) - \
                set(self.fields.keys())
            if unknown_keys:
                raise APIException(
                    "Got unknown fields: {}".format(unknown_keys))
        return data

    def get_validation_exclusions(self):
        exclusions = super(CategoryCreateSerializer,
                           self).get_validation_exclusions()
        return exclusions + ['children']


class CategoryReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

    class Meta:
        model = Category
        fields = ('id', 'name')
        read_only_fields = ('id', 'name')


class TreeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    children = RecursiveField(many=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'children')

    def to_representation(self, instance):
        ret = OrderedDict()
        fields = self._readable_fields

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except serializers.SkipField:
                continue

            # do not want [] to appear in response:
            print(field, attribute, field.__class__)
            if isinstance(field, serializers.ListSerializer) and \
                    not len(attribute.values()):
                print('skipped')
                continue

            check_for_none = attribute.pk if isinstance(
                attribute, serializers.PKOnlyObject) else attribute

            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret


class CategoryView(APIView):
    model = Category
    create_serializer = CategoryCreateSerializer
    serializer = TreeSerializer

    def _check_name(self, data):
        if self.model.objects.filter(name=data['name']).first():
            msg = '{}(name={}) already exists. Send DELETE to clear table.'
            raise CategoryNameDuplicate(
                detail=msg.format(
                    self.model.__name__,
                    data['name']
                )
            )

    def create_item(self, siblings, parent=None):
        for s in siblings:
            self.create_serializer(data=s).is_valid(raise_exception=True)
            data = {
                'name': s['name'],
            }
            if parent:
                data['parent'] = parent
            self._check_name(data)
            item = self.model(**data)
            item.save()
            if s.get('children'):
                self.create_item(s['children'], parent=item)

    def post(self, request):
        self.create_serializer(data=request.data).is_valid(
            raise_exception=True)
        try:
            self._check_name(request.data)
            root = self.model(name=request.data['name'])
            root.save()
            self.create_item(request.data['children'], root)
        except (
            CategoryDoesNotExist, CategoryNameDuplicate, APIException
        ) as e:
            self.model.objects.all().delete()
            raise e

        created = [
            self.create_serializer(c).data for c in self.model.objects.all()
        ]

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
