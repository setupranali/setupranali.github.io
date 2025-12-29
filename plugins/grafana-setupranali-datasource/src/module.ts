import { DataSourcePlugin } from '@grafana/data';
import { SetuPranaliDataSource } from './datasource';
import { ConfigEditor } from './components/ConfigEditor';
import { QueryEditor } from './components/QueryEditor';
import { SetuPranaliQuery, SetuPranaliOptions } from './types';

export const plugin = new DataSourcePlugin<SetuPranaliDataSource, SetuPranaliQuery, SetuPranaliOptions>(
  SetuPranaliDataSource
)
  .setConfigEditor(ConfigEditor)
  .setQueryEditor(QueryEditor);

