from collections import OrderedDict

from .models import Category
from .exceptions import APIException

from rest_framework import serializers

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
            if isinstance(field, serializers.ListSerializer) and \
                    not len(attribute.values()):
                continue

            check_for_none = attribute.pk if isinstance(
                attribute, serializers.PKOnlyObject) else attribute

            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret