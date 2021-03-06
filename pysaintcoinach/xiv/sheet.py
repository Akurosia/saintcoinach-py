from abc import abstractmethod
from typing import Union, Type, TypeVar, List, Optional, Tuple, Dict, Generator, Callable, Generic, Iterable, cast

from ..ex.relational.sheet import IRelationalRow, IRelationalSheet
from .. import xiv
from .. import text
from .. import imaging


class IXivRow(IRelationalRow):
    @property
    @abstractmethod
    def source_row(self) -> IRelationalRow: pass

    @property
    @abstractmethod
    def sheet(self) -> 'IXivSheet': pass


class IXivSubRow(IXivRow):
    @property
    @abstractmethod
    def parent_row(self) -> 'IRow': pass

    @property
    @abstractmethod
    def parent_key(self) -> int: pass

T = TypeVar('T', bound=IXivRow)


class IXivSheet(IRelationalSheet[T]):
    @property
    @abstractmethod
    def collection(self) -> 'xiv.XivCollection': pass

    @abstractmethod
    def __getitem__(self, row: int) -> T: pass


class XivRow(IXivRow):
    @property
    def source_row(self): return self.__source_row

    @property
    def sheet(self) -> IXivSheet: return self.__sheet

    def __init__(self, sheet: IXivSheet, source_row: IRelationalRow):
        self.__sheet = sheet
        self.__source_row = source_row

    def __str__(self):
        return str(self.__source_row)

    def __repr__(self):
        return str(self)

    @property
    def default_value(self): return self.__source_row.default_value

    def __getitem__(self, item: Union[int, str, Tuple]) -> object:
        if isinstance(item, tuple):
            return self.__source_row[self.build_column_name(item[0], *item[1:])]
        return self.__source_row[item]

    def get_raw(self, column_name: Union[int, str]) -> object:
        return self.__source_row.get_raw(column_name)

    @property
    def key(self) -> int: return self.__source_row.key

    @staticmethod
    def build_column_name(column: str, *indices: List[int]) -> str:
        return column + ''.join(['[%u]' % i for i in indices])

    def as_image(self, column: str, *indicies: List[int]) -> imaging.ImageFile:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return cast(imaging.ImageFile, self[column])

    def as_string(self, column: str, *indicies: List[int]) -> text.XivString:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return cast(text.XivString, self[column])

    def as_boolean(self, column: str, *indicies: List[int]) -> bool:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return bool(self[column])

    def as_int16(self, column: str, *indicies: List[int]) -> int:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return int(self[column]) & 0xFFFF

    def as_int32(self, column: str, *indicies: List[int]) -> int:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return int(self[column]) & 0xFFFFFFFF

    def as_int64(self, column: str, *indicies: List[int]) -> int:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return int(self[column])

    def as_single(self, column: str, *indicies: List[int]) -> float:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return float(self[column])

    def as_double(self, column: str, *indicies: List[int]) -> float:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return float(self[column])

    def as_quad(self, column: str, *indicies: List[int]) -> int:
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return int(self[column])

    def as_T(self, t_cls: Type, column: str = None, *indicies: List[int]) -> object:
        if column is None:
            column = t_cls.__name__
        if len(indicies) > 0:
            column = self.build_column_name(column, *indicies)
        return cast(t_cls, self[column])


class XivSheet(IXivSheet[T]):
    def __init__(self,
                 t_cls: Type[T],
                 collection: 'xiv.XivCollection',
                 source: IRelationalSheet):
        self.__t_cls = t_cls
        self.__rows = {}  # type: Dict[int, T]
        self.__collection = collection
        self.__source = source

    @property
    def collection(self) -> 'xiv.XivCollection':
        return self.__collection

    def __iter__(self):
        for src_row in self.__source:
            key = src_row.key
            row = self.__rows.get(key)
            if row is None:
                row = self._create_row(src_row)
                self.__rows[key] = row
            yield row

    def _create_row(self, source_row: IRelationalRow) -> T:
        return cast(T, self.__t_cls(self, source_row))

    def __getitem__(self, item):
        def get_row(key):
            row = self.__rows.get(key)
            if row is not None:
                return row

            source_row = self.__source[key]
            row = self._create_row(source_row)
            self.__rows[key] = row
            return row
        if isinstance(item, tuple):
            return get_row(item[0])[item[1]]
        else:
            return get_row(item)

    def indexed_lookup(self, index: str, key: int):
        return self.__source.indexed_lookup(index, key)

    @property
    def name(self): return self.__source.name

    @property
    def header(self): return self.__source.header

    def __len__(self): return len(self.__source)

    def __contains__(self, item): return item in self.__source

    @property
    def keys(self): return self.__source.keys


class XivSubRow(XivRow, IXivSubRow):
    def __init__(self, sheet: IXivSheet, source_row: IRelationalRow):
        super(XivSubRow, self).__init__(sheet, source_row)
        self._source_sub_row = source_row  # type: SubRow

    @property
    def full_key(self): return self._source_sub_row.full_key

    @property
    def parent_row(self): return self._source_sub_row.parent_row

    @property
    def parent_key(self): return self._source_sub_row.parent_row.key

T = TypeVar('T', bound=IXivSubRow)


class XivSheet2(XivSheet[T]):
    def __init__(self,
                 t_cls: Type[T],
                 collection: 'xiv.XivCollection',
                 source: IRelationalSheet):
        self.__t_cls = t_cls
        self.__sub_rows = {}  # type: Dict[Tuple[int, int], T]
        self.__source = source
        super(XivSheet2, self).__init__(t_cls, collection, source)

    def __iter__(self):
        for current_parent in self.__source:
            for src_row in current_parent.sub_rows:
                key = (current_parent.key, src_row.key)
                row = self.__sub_rows.get(key)
                if row is None:
                    row = self._create_sub_row(src_row)
                    self.__sub_rows[key] = row
                yield row

    def _create_sub_row(self, source_row: IRelationalRow) -> T:
        return self.__t_cls(self, source_row)
