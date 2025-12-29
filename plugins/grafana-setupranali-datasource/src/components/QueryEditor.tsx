import React, { useEffect, useState } from 'react';
import { css } from '@emotion/css';
import {
  InlineField,
  Input,
  Select,
  MultiSelect,
  RadioButtonGroup,
  TextArea,
  useStyles2,
} from '@grafana/ui';
import { QueryEditorProps, SelectableValue, GrafanaTheme2 } from '@grafana/data';
import { SetuPranaliDataSource } from '../datasource';
import { SetuPranaliOptions, SetuPranaliQuery, Dataset, defaultQuery } from '../types';

type Props = QueryEditorProps<SetuPranaliDataSource, SetuPranaliQuery, SetuPranaliOptions>;

const getStyles = (theme: GrafanaTheme2) => ({
  row: css`
    display: flex;
    flex-wrap: wrap;
    gap: ${theme.spacing(1)};
    margin-bottom: ${theme.spacing(1)};
  `,
  sqlEditor: css`
    width: 100%;
    min-height: 100px;
    font-family: monospace;
  `,
});

export function QueryEditor({ datasource, query, onChange, onRunQuery }: Props) {
  const styles = useStyles2(getStyles);
  
  // State for available options
  const [datasets, setDatasets] = useState<SelectableValue[]>([]);
  const [dimensions, setDimensions] = useState<SelectableValue[]>([]);
  const [metrics, setMetrics] = useState<SelectableValue[]>([]);
  const [loading, setLoading] = useState(false);

  // Query type options
  const queryTypeOptions = [
    { label: 'Semantic', value: 'semantic' },
    { label: 'SQL', value: 'sql' },
  ];

  // Time granularity options
  const granularityOptions: SelectableValue[] = [
    { label: 'None', value: '' },
    { label: 'Hour', value: 'hour' },
    { label: 'Day', value: 'day' },
    { label: 'Week', value: 'week' },
    { label: 'Month', value: 'month' },
    { label: 'Year', value: 'year' },
  ];

  // Load datasets on mount
  useEffect(() => {
    loadDatasets();
  }, []);

  // Load dimensions/metrics when dataset changes
  useEffect(() => {
    if (query.dataset) {
      loadDatasetDetails(query.dataset);
    }
  }, [query.dataset]);

  const loadDatasets = async () => {
    setLoading(true);
    try {
      const result = await datasource.getDatasets();
      setDatasets(result.map((d) => ({ label: d.text, value: d.value })));
    } catch (error) {
      console.error('Failed to load datasets:', error);
    }
    setLoading(false);
  };

  const loadDatasetDetails = async (datasetId: string) => {
    try {
      const [dims, mets] = await Promise.all([
        datasource.getDimensions(datasetId),
        datasource.getMetrics(datasetId),
      ]);
      
      setDimensions(dims.map((d) => ({ label: d.text, value: d.value })));
      setMetrics(mets.map((m) => ({ label: m.text, value: m.value })));
    } catch (error) {
      console.error('Failed to load dataset details:', error);
    }
  };

  const onQueryTypeChange = (value: string) => {
    onChange({ ...query, queryType: value as 'semantic' | 'sql' });
  };

  const onDatasetChange = (option: SelectableValue) => {
    onChange({ ...query, dataset: option?.value || '' });
    onRunQuery();
  };

  const onDimensionsChange = (options: SelectableValue[]) => {
    onChange({ ...query, dimensions: options.map((o) => o.value) });
  };

  const onMetricsChange = (options: SelectableValue[]) => {
    onChange({ ...query, metrics: options.map((o) => o.value) });
    onRunQuery();
  };

  const onTimeDimensionChange = (option: SelectableValue) => {
    onChange({ ...query, timeDimension: option?.value || '' });
  };

  const onGranularityChange = (option: SelectableValue) => {
    onChange({ ...query, timeGranularity: option?.value || '' });
    onRunQuery();
  };

  const onLimitChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...query, limit: parseInt(event.target.value, 10) || 1000 });
  };

  const onRawSqlChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ ...query, rawSql: event.target.value });
  };

  const onBlur = () => {
    onRunQuery();
  };

  // Apply defaults
  const currentQuery = { ...defaultQuery, ...query };

  return (
    <div>
      {/* Query Type Selector */}
      <div className={styles.row}>
        <InlineField label="Query Type" labelWidth={12}>
          <RadioButtonGroup
            options={queryTypeOptions}
            value={currentQuery.queryType}
            onChange={onQueryTypeChange}
          />
        </InlineField>
      </div>

      {currentQuery.queryType === 'semantic' ? (
        <>
          {/* Dataset Selection */}
          <div className={styles.row}>
            <InlineField label="Dataset" labelWidth={12} tooltip="Select a dataset to query">
              <Select
                width={30}
                options={datasets}
                value={datasets.find((d) => d.value === currentQuery.dataset)}
                onChange={onDatasetChange}
                isLoading={loading}
                placeholder="Select dataset..."
                isClearable
              />
            </InlineField>
          </div>

          {/* Dimensions */}
          <div className={styles.row}>
            <InlineField label="Dimensions" labelWidth={12} tooltip="Group by these dimensions">
              <MultiSelect
                width={50}
                options={dimensions}
                value={dimensions.filter((d) => currentQuery.dimensions?.includes(d.value))}
                onChange={onDimensionsChange}
                onBlur={onBlur}
                placeholder="Select dimensions..."
              />
            </InlineField>
          </div>

          {/* Metrics */}
          <div className={styles.row}>
            <InlineField label="Metrics" labelWidth={12} tooltip="Metrics to aggregate">
              <MultiSelect
                width={50}
                options={metrics}
                value={metrics.filter((m) => currentQuery.metrics?.includes(m.value))}
                onChange={onMetricsChange}
                placeholder="Select metrics..."
              />
            </InlineField>
          </div>

          {/* Time Settings */}
          <div className={styles.row}>
            <InlineField label="Time Dimension" labelWidth={12} tooltip="Dimension to use for time filtering">
              <Select
                width={20}
                options={[{ label: 'None', value: '' }, ...dimensions]}
                value={dimensions.find((d) => d.value === currentQuery.timeDimension) || { label: 'None', value: '' }}
                onChange={onTimeDimensionChange}
                isClearable
              />
            </InlineField>

            <InlineField label="Granularity" labelWidth={10}>
              <Select
                width={15}
                options={granularityOptions}
                value={granularityOptions.find((g) => g.value === currentQuery.timeGranularity)}
                onChange={onGranularityChange}
              />
            </InlineField>

            <InlineField label="Limit" labelWidth={8}>
              <Input
                width={10}
                type="number"
                value={currentQuery.limit}
                onChange={onLimitChange}
                onBlur={onBlur}
              />
            </InlineField>
          </div>
        </>
      ) : (
        <>
          {/* SQL Mode */}
          <div className={styles.row}>
            <InlineField label="Dataset" labelWidth={12} tooltip="Dataset for RLS context">
              <Select
                width={30}
                options={datasets}
                value={datasets.find((d) => d.value === currentQuery.dataset)}
                onChange={onDatasetChange}
                isLoading={loading}
                placeholder="Select dataset..."
                isClearable
              />
            </InlineField>
          </div>

          <div className={styles.row}>
            <InlineField label="SQL" labelWidth={12} grow tooltip="Raw SQL query">
              <TextArea
                className={styles.sqlEditor}
                value={currentQuery.rawSql || ''}
                onChange={onRawSqlChange}
                onBlur={onBlur}
                placeholder="SELECT region, SUM(amount) as revenue FROM orders GROUP BY region"
                rows={5}
              />
            </InlineField>
          </div>
        </>
      )}
    </div>
  );
}

