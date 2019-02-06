# coding: utf-8
import re

from jinja2 import Template
from sqlalchemy import create_engine

DB = '数据库'

ENGINE = create_engine(
    'mysql://%s:%s@%s/%s?charset=utf8' % ('username', 'password', '127.0.0.1',
                                          DB),
    convert_unicode=True,
    echo=False)


GORM_STURCT_TEMPLATE = '''
//{{table.class_name}} {{table.desc}}
type {{table.class_name}} struct {
    {%- for column in table.columns | sort(attribute='id') %}
    {{column.name}}   {{column.field}}    `{{column.type}}` //{{column.comment}}
    {%- endfor %}
}

'''


class Table:
    def __init__(self, class_name, table_name, engine, columns, desc):
        self.class_name, self.table_name = class_name, table_name
        self.engine, self.charset = engine, 'utf8'
        self.columns = columns
        self.desc = desc


class Column:
    def __init__(self, _id, name, field, _type, comment):
        self.id = _id
        self.name = name
        self.field, self.type = field, _type
        self.comment = comment

    def __repr__(self):
        self.__str__(self)

    def __str__(self):
        return '%s %s %s' % (self.name, self.field, self._type)


def load_tables():
    '''加载表
    '''
    tables = []
    with ENGINE.connect() as con:
        rows = con.execute('show tables').fetchall()
        if rows:
            tables = [y for x in rows for y in x]
    return tables


def _mapping_table_name(table_name):
    char_arr = (x.title() for x in table_name.split('_'))
    #return ''.join(char_arr)
    arr = []
    for x in char_arr:
        if x == 'Id':
            x = 'ID'
        arr.append(x)
    return ''.join(arr)


TYPE_MAPPING = {
    'int': 'int',
    'tinyint': 'int',
    'bigint': 'int',
    'long': 'int',
    'smallint': 'int',
    'varchar': 'string',
    'datetime': 'time.Time',
    'longtext': 'string',
    'decimal': 'float32',
    'date': 'time.Time',
    'char': 'string',
}

RE_TYPE = re.compile(r'\(')


def _mapping_columns(table_desc):
    '''ORDINAL_POSITION, COLUMN_KEY, COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, EXTRA
    '''
    columns = []
    for _id, key, name, _type, comment, extra in table_desc:
        field = TYPE_MAPPING[RE_TYPE.split(_type)[0]]
        other = []
        if key.lower() == 'pri':
            other.append('PRIMARY_KEY')
        if extra.lower() == 'auto_increment':
            other.append('AUTO_INCREMENT')
        g_type = 'gorm:"type:{type};{extra}"'.format(
            type=_type, extra=';'.join(other))
        name = _mapping_table_name(name)
        column = Column(_id, name, field, g_type, comment)
        columns.append(column)
    return columns


def mapping_table(tables):
    table_struct = []
    for table in tables:
        with ENGINE.connect() as con:
            status = con.execute("show table status from %s where name='%s'" %
                                 (DB, table)).fetchone()
            columns = con.execute(
                '''select ORDINAL_POSITION, COLUMN_KEY, COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, EXTRA 
                FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '%s' AND table_name = '%s'
            ''' % (DB, table)).fetchall()
            class_name = _mapping_table_name(status['Name'])
            table_struct.append(
                Table(
                    class_name=class_name,
                    table_name=status['Name'],
                    engine=status['Engine'],
                    columns=_mapping_columns(columns),
                    desc=status['Comment']))
    return table_struct


def gen_struct(table_structs):
    for table in table_structs:
        table_tpl = Template(GORM_STURCT_TEMPLATE)
        string = table_tpl.render(table=table)
        print string


def main():
    tables = load_tables()
    if not tables:
        raise u'请先创建表'
    table_structs = mapping_table(tables)
    gen_struct(table_structs)


if __name__ == "__main__":
    main()
