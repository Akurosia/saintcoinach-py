from abc import abstractmethod
from typing import List
from collections import OrderedDict
import json

from ex.sheet import IRow
from ex.datasheet import IDataRow
from ex.relational.sheet import IRelationalRow, IRelationalSheet
from ex.relational.valueconverter import IValueConverter


class IRowProducer(object):
    @abstractmethod
    def get_row(self, sheet: IRelationalSheet, key: int) -> IRow:
        pass


class PrimaryKeyRowProducer(IRowProducer):
    def get_row(self, sheet: IRelationalSheet, key: int):
        return sheet[key]


class IndexedRowProducer(IRowProducer):
    @property
    def key_column_name(self) -> str:
        return self.__key_column_name

    @key_column_name.setter
    def key_column_name(self, value):
        self.__key_column_name = value

    def __init__(self, key_column_name: str = None):
        self.__key_column_name = key_column_name

    def get_row(self, sheet: IRelationalSheet, key: int):
        return sheet.indexed_lookup(self.key_column_name, key)


class IProjectable(object):
    @abstractmethod
    def project(self, row: IRow) -> object:
        pass


class IdentityProjection(IProjectable):
    def project(self, row: IRow):
        return row


class ColumnProjection(IProjectable):
    @property
    def projected_column_name(self) -> str:
        return self.__projected_column_name

    @projected_column_name.setter
    def projected_column_name(self, value: str):
        self.__projected_column_name = value

    def __init__(self, projected_column_name: str):
        self.__projected_column_name = projected_column_name

    def project(self, row: IRow):
        relational_row = row  # type: IRelationalRow
        return relational_row[self.projected_column_name]


class SheetLinkData(object):
    def __init__(self, **kwargs):
        self.sheet_name = kwargs.get('sheet_name', None)  # type: str
        self.projected_column_name = kwargs.get('projected_column_name', None)  # type: str
        self.key_column_name = kwargs.get('key_column_name', None)  # type: str
        self.row_producer = kwargs.get('row_producer', None)  # type: IRowProducer
        self.projection = kwargs.get('projection', None)  # type: IProjectable

    def to_json(self):
        obj = OrderedDict()
        obj['sheet'] = self.sheet_name
        if self.projected_column_name is not None:
            obj['project'] = self.projected_column_name
        if self.key_column_name is not None:
            obj['key'] = self.key_column_name

        return obj

    @staticmethod
    def from_json(obj: dict):
        data = SheetLinkData(sheet_name=str(obj['sheet']))

        if obj.get('project', None) is None:
            data.projection = IdentityProjection()
        else:
            data.projected_column_name = str(obj['project'])
            data.projection = ColumnProjection(
                projected_column_name=data.projected_column_name)

        if obj.get('key', None) is None:
            data.row_producer = PrimaryKeyRowProducer()
        else:
            data.key_column_name = str(obj['key'])
            data.row_producer = IndexedRowProducer(
                key_column_name=data.key_column_name)

        return data


class ComplexLinkConverter(IValueConverter):
    @property
    def target_type_name(self): return 'Row'

    @property
    def target_type(self): return type(IRelationalRow)

    def __init__(self, links: 'List[SheetLinkData]'):
        self.__links = links  # type: List[SheetLinkData]

    def __repr__(self):
        return "%s()" % (self.__class__.__name__)

    def convert(self, row: IDataRow, raw_value: object):
        key = int(raw_value)
        if key == 0:
            return None
        coll = row.sheet.collection

        for link in self.__links:
            sheet = coll.get_sheet(link.sheet_name)  # type: IRelationalSheet
            result = link.row_producer.get_row(sheet, key)
            if result is None:
                continue

            return link.projection.project(result)

        return raw_value

    def to_json(self):
        obj = OrderedDict()
        obj['type'] = 'complexlink'
        obj['links'] = [l.to_json() for l in self.__links]
        return obj

    @staticmethod
    def from_json(obj: dict):
        return ComplexLinkConverter(
            links=[SheetLinkData.from_json(o) for o in obj['links']])
