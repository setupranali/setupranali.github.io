import React, { ChangeEvent } from 'react';
import { InlineField, Input, SecretInput, Switch, FieldSet } from '@grafana/ui';
import { DataSourcePluginOptionsEditorProps } from '@grafana/data';
import { SetuPranaliOptions, SetuPranaliSecureOptions } from '../types';

interface Props extends DataSourcePluginOptionsEditorProps<SetuPranaliOptions, SetuPranaliSecureOptions> {}

export function ConfigEditor(props: Props) {
  const { onOptionsChange, options } = props;
  const { jsonData, secureJsonFields, secureJsonData } = options;

  const onUrlChange = (event: ChangeEvent<HTMLInputElement>) => {
    onOptionsChange({
      ...options,
      url: event.target.value,
      jsonData: {
        ...jsonData,
        url: event.target.value,
      },
    });
  };

  const onDefaultDatasetChange = (event: ChangeEvent<HTMLInputElement>) => {
    onOptionsChange({
      ...options,
      jsonData: {
        ...jsonData,
        defaultDataset: event.target.value,
      },
    });
  };

  const onCacheEnabledChange = (event: ChangeEvent<HTMLInputElement>) => {
    onOptionsChange({
      ...options,
      jsonData: {
        ...jsonData,
        cacheEnabled: event.target.checked,
      },
    });
  };

  const onCacheTTLChange = (event: ChangeEvent<HTMLInputElement>) => {
    onOptionsChange({
      ...options,
      jsonData: {
        ...jsonData,
        cacheTTL: parseInt(event.target.value, 10) || 300,
      },
    });
  };

  const onAPIKeyChange = (event: ChangeEvent<HTMLInputElement>) => {
    onOptionsChange({
      ...options,
      secureJsonData: {
        ...secureJsonData,
        apiKey: event.target.value,
      },
    });
  };

  const onResetAPIKey = () => {
    onOptionsChange({
      ...options,
      secureJsonFields: {
        ...secureJsonFields,
        apiKey: false,
      },
      secureJsonData: {
        ...secureJsonData,
        apiKey: '',
      },
    });
  };

  return (
    <>
      <FieldSet label="Connection">
        <InlineField label="URL" labelWidth={20} tooltip="SetuPranali server URL (e.g., http://localhost:8080)">
          <Input
            width={40}
            value={options.url || ''}
            placeholder="http://localhost:8080"
            onChange={onUrlChange}
          />
        </InlineField>

        <InlineField label="API Key" labelWidth={20} tooltip="API key for authentication">
          <SecretInput
            width={40}
            isConfigured={secureJsonFields?.apiKey}
            value={secureJsonData?.apiKey || ''}
            placeholder="Enter API key"
            onReset={onResetAPIKey}
            onChange={onAPIKeyChange}
          />
        </InlineField>
      </FieldSet>

      <FieldSet label="Defaults">
        <InlineField label="Default Dataset" labelWidth={20} tooltip="Default dataset for new queries">
          <Input
            width={40}
            value={jsonData?.defaultDataset || ''}
            placeholder="orders"
            onChange={onDefaultDatasetChange}
          />
        </InlineField>
      </FieldSet>

      <FieldSet label="Caching">
        <InlineField label="Enable Cache" labelWidth={20} tooltip="Enable query result caching">
          <Switch
            value={jsonData?.cacheEnabled || false}
            onChange={onCacheEnabledChange}
          />
        </InlineField>

        {jsonData?.cacheEnabled && (
          <InlineField label="Cache TTL" labelWidth={20} tooltip="Cache time-to-live in seconds">
            <Input
              width={40}
              type="number"
              value={jsonData?.cacheTTL || 300}
              placeholder="300"
              onChange={onCacheTTLChange}
            />
          </InlineField>
        )}
      </FieldSet>
    </>
  );
}

