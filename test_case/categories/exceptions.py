from rest_framework.exceptions import APIException as BaseAPIException


class APIException(BaseAPIException):
    status_code = 422


class CategoryDoesNotExist(APIException):
    status_code = 404


class CategoryNameDuplicate(APIException):
    status_code = 409