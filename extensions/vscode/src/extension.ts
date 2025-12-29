/**
 * SetuPranali VS Code Extension
 * 
 * Provides:
 * - IntelliSense for catalog.yaml
 * - Real-time validation
 * - Query preview
 * - Import from dbt/LookML/Cube.js
 */

import * as vscode from 'vscode';
import * as yaml from 'yaml';
import axios from 'axios';

// =============================================================================
// Types
// =============================================================================

interface Dataset {
    id: string;
    name: string;
    description?: string;
    dimensions: Dimension[];
    metrics: Metric[];
}

interface Dimension {
    name: string;
    sql: string;
    type?: string;
    description?: string;
}

interface Metric {
    name: string;
    sql: string;
    description?: string;
}

interface Catalog {
    version?: string;
    datasets: Dataset[];
    joins?: any[];
    calculated_metrics?: any[];
}

interface ValidationError {
    line: number;
    column: number;
    message: string;
    severity: 'error' | 'warning' | 'info';
}

// =============================================================================
// Extension Activation
// =============================================================================

let diagnosticCollection: vscode.DiagnosticCollection;
let catalogCache: Map<string, Catalog> = new Map();

export function activate(context: vscode.ExtensionContext) {
    console.log('SetuPranali extension activated');

    // Create diagnostic collection
    diagnosticCollection = vscode.languages.createDiagnosticCollection('setupranali');
    context.subscriptions.push(diagnosticCollection);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('setupranali.validateCatalog', validateCatalog),
        vscode.commands.registerCommand('setupranali.previewQuery', previewQuery),
        vscode.commands.registerCommand('setupranali.syncWithServer', syncWithServer),
        vscode.commands.registerCommand('setupranali.generateFromSource', generateFromSource),
        vscode.commands.registerCommand('setupranali.importDbt', importDbt),
        vscode.commands.registerCommand('setupranali.importLookML', importLookML),
        vscode.commands.registerCommand('setupranali.importCube', importCube)
    );

    // Register completion provider
    const completionProvider = vscode.languages.registerCompletionItemProvider(
        [
            { language: 'yaml', pattern: '**/catalog.{yaml,yml}' },
            { language: 'setupranali-catalog' }
        ],
        new SetuPranaliCompletionProvider(),
        '.', ':', ' '
    );
    context.subscriptions.push(completionProvider);

    // Register hover provider
    const hoverProvider = vscode.languages.registerHoverProvider(
        [
            { language: 'yaml', pattern: '**/catalog.{yaml,yml}' },
            { language: 'setupranali-catalog' }
        ],
        new SetuPranaliHoverProvider()
    );
    context.subscriptions.push(hoverProvider);

    // Register definition provider
    const definitionProvider = vscode.languages.registerDefinitionProvider(
        [
            { language: 'yaml', pattern: '**/catalog.{yaml,yml}' },
            { language: 'setupranali-catalog' }
        ],
        new SetuPranaliDefinitionProvider()
    );
    context.subscriptions.push(definitionProvider);

    // Watch for document changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeTextDocument((e) => {
            if (isCatalogFile(e.document)) {
                validateDocument(e.document);
            }
        }),
        vscode.workspace.onDidOpenTextDocument((document) => {
            if (isCatalogFile(document)) {
                validateDocument(document);
            }
        })
    );

    // Register tree view
    const treeDataProvider = new CatalogTreeDataProvider();
    vscode.window.registerTreeDataProvider('setupranaliExplorer', treeDataProvider);

    // Validate open catalog files
    vscode.workspace.textDocuments.forEach((document) => {
        if (isCatalogFile(document)) {
            validateDocument(document);
        }
    });
}

export function deactivate() {
    diagnosticCollection.dispose();
}

// =============================================================================
// Helpers
// =============================================================================

function isCatalogFile(document: vscode.TextDocument): boolean {
    return document.fileName.endsWith('catalog.yaml') || 
           document.fileName.endsWith('catalog.yml');
}

function getConfig(): vscode.WorkspaceConfiguration {
    return vscode.workspace.getConfiguration('setupranali');
}

async function getServerUrl(): Promise<string> {
    return getConfig().get<string>('serverUrl') || 'http://localhost:8080';
}

async function getApiKey(): Promise<string> {
    return getConfig().get<string>('apiKey') || '';
}

function parseCatalog(content: string): Catalog | null {
    try {
        return yaml.parse(content) as Catalog;
    } catch (e) {
        return null;
    }
}

// =============================================================================
// Validation
// =============================================================================

async function validateCatalog() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || !isCatalogFile(editor.document)) {
        vscode.window.showWarningMessage('Open a catalog.yaml file first');
        return;
    }

    await validateDocument(editor.document);
    vscode.window.showInformationMessage('Catalog validation complete');
}

async function validateDocument(document: vscode.TextDocument) {
    const config = getConfig();
    if (!config.get<boolean>('enableValidation')) {
        return;
    }

    const content = document.getText();
    const errors: ValidationError[] = [];
    const diagnostics: vscode.Diagnostic[] = [];

    // Parse YAML
    let catalog: Catalog | null = null;
    try {
        catalog = yaml.parse(content) as Catalog;
        catalogCache.set(document.uri.toString(), catalog);
    } catch (e: any) {
        errors.push({
            line: e.linePos?.[0]?.line || 1,
            column: e.linePos?.[0]?.col || 1,
            message: `YAML parse error: ${e.message}`,
            severity: 'error'
        });
    }

    if (catalog) {
        // Validate structure
        errors.push(...validateCatalogStructure(catalog, content));
        
        // Validate with server if configured
        const serverUrl = await getServerUrl();
        const apiKey = await getApiKey();
        
        if (serverUrl && apiKey) {
            try {
                const serverErrors = await validateWithServer(catalog, serverUrl, apiKey);
                errors.push(...serverErrors);
            } catch (e) {
                // Server validation failed, continue with local validation only
            }
        }
    }

    // Convert errors to diagnostics
    for (const error of errors) {
        const range = new vscode.Range(
            error.line - 1, 
            error.column - 1, 
            error.line - 1, 
            1000
        );
        
        const severity = error.severity === 'error' 
            ? vscode.DiagnosticSeverity.Error
            : error.severity === 'warning'
            ? vscode.DiagnosticSeverity.Warning
            : vscode.DiagnosticSeverity.Information;

        diagnostics.push(new vscode.Diagnostic(range, error.message, severity));
    }

    diagnosticCollection.set(document.uri, diagnostics);
}

function validateCatalogStructure(catalog: Catalog, content: string): ValidationError[] {
    const errors: ValidationError[] = [];
    const lines = content.split('\n');

    // Check for datasets
    if (!catalog.datasets || !Array.isArray(catalog.datasets)) {
        errors.push({
            line: 1,
            column: 1,
            message: 'Catalog must have a "datasets" array',
            severity: 'error'
        });
        return errors;
    }

    const datasetIds = new Set<string>();

    for (let i = 0; i < catalog.datasets.length; i++) {
        const dataset = catalog.datasets[i];
        const lineNum = findLineNumber(lines, `id: ${dataset.id}`) || i + 1;

        // Check required fields
        if (!dataset.id) {
            errors.push({
                line: lineNum,
                column: 1,
                message: `Dataset ${i + 1} is missing required "id" field`,
                severity: 'error'
            });
        }

        // Check for duplicate IDs
        if (dataset.id && datasetIds.has(dataset.id)) {
            errors.push({
                line: lineNum,
                column: 1,
                message: `Duplicate dataset ID: ${dataset.id}`,
                severity: 'error'
            });
        }
        datasetIds.add(dataset.id);

        // Check SQL
        if (!dataset.sql && dataset.id) {
            errors.push({
                line: lineNum,
                column: 1,
                message: `Dataset "${dataset.id}" is missing SQL definition`,
                severity: 'warning'
            });
        }

        // Check dimensions
        if (!dataset.dimensions || dataset.dimensions.length === 0) {
            errors.push({
                line: lineNum,
                column: 1,
                message: `Dataset "${dataset.id}" has no dimensions`,
                severity: 'warning'
            });
        }

        // Check metrics
        if (!dataset.metrics || dataset.metrics.length === 0) {
            errors.push({
                line: lineNum,
                column: 1,
                message: `Dataset "${dataset.id}" has no metrics`,
                severity: 'info'
            });
        }

        // Validate dimension names are unique
        const dimNames = new Set<string>();
        for (const dim of dataset.dimensions || []) {
            if (dimNames.has(dim.name)) {
                const dimLine = findLineNumber(lines, `name: ${dim.name}`) || lineNum;
                errors.push({
                    line: dimLine,
                    column: 1,
                    message: `Duplicate dimension name in "${dataset.id}": ${dim.name}`,
                    severity: 'error'
                });
            }
            dimNames.add(dim.name);
        }

        // Validate metric names are unique
        const metricNames = new Set<string>();
        for (const metric of dataset.metrics || []) {
            if (metricNames.has(metric.name)) {
                const metricLine = findLineNumber(lines, `name: ${metric.name}`) || lineNum;
                errors.push({
                    line: metricLine,
                    column: 1,
                    message: `Duplicate metric name in "${dataset.id}": ${metric.name}`,
                    severity: 'error'
                });
            }
            metricNames.add(metric.name);
        }
    }

    // Validate joins
    for (const join of catalog.joins || []) {
        if (!datasetIds.has(join.left_dataset)) {
            errors.push({
                line: findLineNumber(lines, `left_dataset: ${join.left_dataset}`) || 1,
                column: 1,
                message: `Join references unknown dataset: ${join.left_dataset}`,
                severity: 'error'
            });
        }
        if (!datasetIds.has(join.right_dataset)) {
            errors.push({
                line: findLineNumber(lines, `right_dataset: ${join.right_dataset}`) || 1,
                column: 1,
                message: `Join references unknown dataset: ${join.right_dataset}`,
                severity: 'error'
            });
        }
    }

    return errors;
}

function findLineNumber(lines: string[], searchStr: string): number | null {
    for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes(searchStr)) {
            return i + 1;
        }
    }
    return null;
}

async function validateWithServer(
    catalog: Catalog, 
    serverUrl: string, 
    apiKey: string
): Promise<ValidationError[]> {
    try {
        const response = await axios.post(
            `${serverUrl}/v1/catalog/validate`,
            catalog,
            {
                headers: {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        return (response.data.errors || []).map((e: any) => ({
            line: e.line || 1,
            column: e.column || 1,
            message: e.message,
            severity: e.severity || 'error'
        }));
    } catch (e) {
        return [];
    }
}

// =============================================================================
// Completion Provider
// =============================================================================

class SetuPranaliCompletionProvider implements vscode.CompletionItemProvider {
    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.CompletionItem[]> {
        const config = getConfig();
        if (!config.get<boolean>('enableAutoComplete')) {
            return [];
        }

        const lineText = document.lineAt(position).text;
        const linePrefix = lineText.substring(0, position.character);

        // Get catalog from cache
        const catalog = catalogCache.get(document.uri.toString());

        const items: vscode.CompletionItem[] = [];

        // Top-level completions
        if (linePrefix.trim() === '' || linePrefix.endsWith('  ')) {
            items.push(...this.getTopLevelCompletions());
        }

        // Dataset property completions
        if (linePrefix.includes('- id:') || linePrefix.match(/^\s+-\s*$/)) {
            items.push(...this.getDatasetCompletions());
        }

        // Dimension completions
        if (linePrefix.includes('dimensions:') || linePrefix.match(/dimensions:\s*$/)) {
            items.push(...this.getDimensionCompletions());
        }

        // Metric completions
        if (linePrefix.includes('metrics:') || linePrefix.match(/metrics:\s*$/)) {
            items.push(...this.getMetricCompletions());
        }

        // Type completions
        if (linePrefix.match(/type:\s*$/)) {
            items.push(...this.getTypeCompletions());
        }

        // SQL function completions
        if (linePrefix.match(/sql:\s*[\w\s]*$/i)) {
            items.push(...this.getSqlCompletions());
        }

        return items;
    }

    private getTopLevelCompletions(): vscode.CompletionItem[] {
        return [
            this.createSnippet('version', 'version: "${1:1.0}"'),
            this.createSnippet('datasets', 'datasets:\n  - id: ${1:dataset_name}\n    name: ${2:Dataset Name}\n    sql: SELECT * FROM ${3:table}\n    dimensions:\n      - name: ${4:dimension}\n        sql: ${4:dimension}\n    metrics:\n      - name: ${5:metric}\n        sql: ${6:COUNT(*)}'),
            this.createSnippet('joins', 'joins:\n  - left_dataset: ${1:left}\n    right_dataset: ${2:right}\n    join_type: ${3|left,inner,right,full|}\n    left_key: ${4:key}\n    right_key: ${5:key}'),
            this.createSnippet('calculated_metrics', 'calculated_metrics:\n  - name: ${1:metric_name}\n    expression: "{${2:base_metric}} / NULLIF({${3:divisor}}, 0)"')
        ];
    }

    private getDatasetCompletions(): vscode.CompletionItem[] {
        return [
            this.createSnippet('dataset', '- id: ${1:dataset_id}\n  name: ${2:Dataset Name}\n  description: ${3:Description}\n  sql: ${4:SELECT * FROM table}\n  dimensions:\n    - name: ${5:dim}\n      sql: ${5:dim}\n  metrics:\n    - name: ${6:metric}\n      sql: ${7:COUNT(*)}'),
            this.createProperty('id', 'Unique identifier for the dataset'),
            this.createProperty('name', 'Human-readable name'),
            this.createProperty('description', 'Dataset description'),
            this.createProperty('sql', 'SQL query or table reference'),
            this.createProperty('dimensions', 'List of dimensions'),
            this.createProperty('metrics', 'List of metrics'),
            this.createProperty('tags', 'Tags for categorization'),
            this.createProperty('rls_field', 'Row-level security field')
        ];
    }

    private getDimensionCompletions(): vscode.CompletionItem[] {
        return [
            this.createSnippet('dimension', '- name: ${1:dimension_name}\n  sql: ${2:column_name}\n  type: ${3|string,number,date,datetime,boolean|}'),
            this.createProperty('name', 'Dimension name'),
            this.createProperty('sql', 'SQL expression'),
            this.createProperty('type', 'Data type'),
            this.createProperty('description', 'Dimension description')
        ];
    }

    private getMetricCompletions(): vscode.CompletionItem[] {
        return [
            this.createSnippet('count', '- name: ${1:count}\n  sql: COUNT(*)'),
            this.createSnippet('sum', '- name: ${1:total}\n  sql: SUM(${2:column})'),
            this.createSnippet('avg', '- name: ${1:average}\n  sql: AVG(${2:column})'),
            this.createSnippet('count_distinct', '- name: ${1:unique_count}\n  sql: COUNT(DISTINCT ${2:column})'),
            this.createProperty('name', 'Metric name'),
            this.createProperty('sql', 'SQL aggregation'),
            this.createProperty('description', 'Metric description')
        ];
    }

    private getTypeCompletions(): vscode.CompletionItem[] {
        return [
            this.createValue('string'),
            this.createValue('number'),
            this.createValue('date'),
            this.createValue('datetime'),
            this.createValue('boolean')
        ];
    }

    private getSqlCompletions(): vscode.CompletionItem[] {
        return [
            this.createFunction('COUNT', 'COUNT(*)', 'Count rows'),
            this.createFunction('COUNT_DISTINCT', 'COUNT(DISTINCT ${1:column})', 'Count distinct values'),
            this.createFunction('SUM', 'SUM(${1:column})', 'Sum values'),
            this.createFunction('AVG', 'AVG(${1:column})', 'Average value'),
            this.createFunction('MIN', 'MIN(${1:column})', 'Minimum value'),
            this.createFunction('MAX', 'MAX(${1:column})', 'Maximum value'),
            this.createFunction('COALESCE', 'COALESCE(${1:column}, ${2:default})', 'Return first non-null'),
            this.createFunction('NULLIF', 'NULLIF(${1:column}, ${2:value})', 'Return null if equal'),
            this.createFunction('CASE', 'CASE WHEN ${1:condition} THEN ${2:value} ELSE ${3:default} END', 'Conditional expression')
        ];
    }

    private createSnippet(label: string, snippet: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Snippet);
        item.insertText = new vscode.SnippetString(snippet);
        return item;
    }

    private createProperty(label: string, description: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Property);
        item.insertText = `${label}: `;
        item.documentation = description;
        return item;
    }

    private createValue(label: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Value);
        return item;
    }

    private createFunction(label: string, snippet: string, description: string): vscode.CompletionItem {
        const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Function);
        item.insertText = new vscode.SnippetString(snippet);
        item.documentation = description;
        return item;
    }
}

// =============================================================================
// Hover Provider
// =============================================================================

class SetuPranaliHoverProvider implements vscode.HoverProvider {
    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Hover> {
        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) {
            return null;
        }

        const word = document.getText(wordRange);
        const catalog = catalogCache.get(document.uri.toString());

        if (!catalog) {
            return null;
        }

        // Check if hovering over a dataset ID
        for (const dataset of catalog.datasets || []) {
            if (dataset.id === word) {
                const content = new vscode.MarkdownString();
                content.appendMarkdown(`**Dataset: ${dataset.name || dataset.id}**\n\n`);
                if (dataset.description) {
                    content.appendMarkdown(`${dataset.description}\n\n`);
                }
                content.appendMarkdown(`- **Dimensions**: ${dataset.dimensions?.length || 0}\n`);
                content.appendMarkdown(`- **Metrics**: ${dataset.metrics?.length || 0}\n`);
                return new vscode.Hover(content, wordRange);
            }

            // Check dimensions
            for (const dim of dataset.dimensions || []) {
                if (dim.name === word) {
                    const content = new vscode.MarkdownString();
                    content.appendMarkdown(`**Dimension: ${dim.name}**\n\n`);
                    content.appendMarkdown(`- **Type**: ${dim.type || 'string'}\n`);
                    content.appendMarkdown(`- **SQL**: \`${dim.sql}\`\n`);
                    if (dim.description) {
                        content.appendMarkdown(`\n${dim.description}`);
                    }
                    return new vscode.Hover(content, wordRange);
                }
            }

            // Check metrics
            for (const metric of dataset.metrics || []) {
                if (metric.name === word) {
                    const content = new vscode.MarkdownString();
                    content.appendMarkdown(`**Metric: ${metric.name}**\n\n`);
                    content.appendMarkdown(`- **SQL**: \`${metric.sql}\`\n`);
                    if (metric.description) {
                        content.appendMarkdown(`\n${metric.description}`);
                    }
                    return new vscode.Hover(content, wordRange);
                }
            }
        }

        return null;
    }
}

// =============================================================================
// Definition Provider
// =============================================================================

class SetuPranaliDefinitionProvider implements vscode.DefinitionProvider {
    provideDefinition(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Definition> {
        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) {
            return null;
        }

        const word = document.getText(wordRange);
        const content = document.getText();
        const lines = content.split('\n');

        // Find definition of dataset, dimension, or metric
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes(`id: ${word}`) || 
                lines[i].includes(`name: ${word}`)) {
                return new vscode.Location(
                    document.uri,
                    new vscode.Position(i, 0)
                );
            }
        }

        return null;
    }
}

// =============================================================================
// Tree Data Provider
// =============================================================================

class CatalogTreeDataProvider implements vscode.TreeDataProvider<CatalogTreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<CatalogTreeItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: CatalogTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: CatalogTreeItem): Promise<CatalogTreeItem[]> {
        if (!element) {
            // Root level - find catalog files and show datasets
            const catalogs = await vscode.workspace.findFiles('**/catalog.{yaml,yml}', '**/node_modules/**');
            
            if (catalogs.length === 0) {
                return [new CatalogTreeItem('No catalog.yaml found', vscode.TreeItemCollapsibleState.None)];
            }

            const items: CatalogTreeItem[] = [];
            
            for (const catalogUri of catalogs) {
                const doc = await vscode.workspace.openTextDocument(catalogUri);
                const catalog = parseCatalog(doc.getText());
                
                if (catalog?.datasets) {
                    for (const dataset of catalog.datasets) {
                        items.push(new CatalogTreeItem(
                            dataset.name || dataset.id,
                            vscode.TreeItemCollapsibleState.Collapsed,
                            'dataset',
                            dataset
                        ));
                    }
                }
            }

            return items;
        }

        // Children of dataset
        if (element.contextValue === 'dataset' && element.dataset) {
            const items: CatalogTreeItem[] = [];

            // Dimensions
            if (element.dataset.dimensions?.length > 0) {
                const dimsItem = new CatalogTreeItem(
                    `Dimensions (${element.dataset.dimensions.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'dimensions-folder'
                );
                dimsItem.dataset = element.dataset;
                items.push(dimsItem);
            }

            // Metrics
            if (element.dataset.metrics?.length > 0) {
                const metricsItem = new CatalogTreeItem(
                    `Metrics (${element.dataset.metrics.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'metrics-folder'
                );
                metricsItem.dataset = element.dataset;
                items.push(metricsItem);
            }

            return items;
        }

        // Dimensions folder
        if (element.contextValue === 'dimensions-folder' && element.dataset) {
            return element.dataset.dimensions.map(dim => 
                new CatalogTreeItem(dim.name, vscode.TreeItemCollapsibleState.None, 'dimension')
            );
        }

        // Metrics folder
        if (element.contextValue === 'metrics-folder' && element.dataset) {
            return element.dataset.metrics.map(metric => 
                new CatalogTreeItem(metric.name, vscode.TreeItemCollapsibleState.None, 'metric')
            );
        }

        return [];
    }
}

class CatalogTreeItem extends vscode.TreeItem {
    dataset?: Dataset;

    constructor(
        label: string,
        collapsibleState: vscode.TreeItemCollapsibleState,
        contextValue?: string,
        dataset?: Dataset
    ) {
        super(label, collapsibleState);
        this.contextValue = contextValue;
        this.dataset = dataset;

        // Set icons based on type
        if (contextValue === 'dataset') {
            this.iconPath = new vscode.ThemeIcon('table');
        } else if (contextValue === 'dimension') {
            this.iconPath = new vscode.ThemeIcon('symbol-field');
        } else if (contextValue === 'metric') {
            this.iconPath = new vscode.ThemeIcon('symbol-number');
        } else if (contextValue === 'dimensions-folder') {
            this.iconPath = new vscode.ThemeIcon('folder');
        } else if (contextValue === 'metrics-folder') {
            this.iconPath = new vscode.ThemeIcon('folder');
        }
    }
}

// =============================================================================
// Commands
// =============================================================================

async function previewQuery() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || !isCatalogFile(editor.document)) {
        vscode.window.showWarningMessage('Open a catalog.yaml file first');
        return;
    }

    const catalog = catalogCache.get(editor.document.uri.toString());
    if (!catalog?.datasets?.length) {
        vscode.window.showWarningMessage('No datasets found in catalog');
        return;
    }

    // Pick a dataset
    const datasetPick = await vscode.window.showQuickPick(
        catalog.datasets.map(d => ({
            label: d.name || d.id,
            description: d.id,
            dataset: d
        })),
        { placeHolder: 'Select a dataset to preview' }
    );

    if (!datasetPick) {
        return;
    }

    // Generate sample query
    const dataset = datasetPick.dataset;
    const dimensions = dataset.dimensions?.slice(0, 2).map(d => d.name) || [];
    const metrics = dataset.metrics?.slice(0, 2).map(m => m.name) || [];

    const query = {
        dataset: dataset.id,
        dimensions,
        metrics
    };

    // Show query in new document
    const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(query, null, 2),
        language: 'json'
    });
    await vscode.window.showTextDocument(doc);
}

async function syncWithServer() {
    const serverUrl = await getServerUrl();
    const apiKey = await getApiKey();

    if (!apiKey) {
        vscode.window.showWarningMessage('Configure setupranali.apiKey in settings');
        return;
    }

    vscode.window.showInformationMessage(`Syncing with server: ${serverUrl}`);
    // Implementation would sync catalog with server
}

async function generateFromSource() {
    vscode.window.showInformationMessage('Generate from source: Coming soon');
}

async function importDbt() {
    const manifestPath = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        filters: { 'JSON': ['json'] },
        title: 'Select dbt manifest.json'
    });

    if (!manifestPath?.[0]) {
        return;
    }

    vscode.window.showInformationMessage(`Importing from dbt: ${manifestPath[0].fsPath}`);
    // Implementation would call dbt_integration
}

async function importLookML() {
    const projectPath = await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        title: 'Select LookML project folder'
    });

    if (!projectPath?.[0]) {
        return;
    }

    vscode.window.showInformationMessage(`Importing from LookML: ${projectPath[0].fsPath}`);
    // Implementation would call lookml_import
}

async function importCube() {
    const schemaPath = await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        title: 'Select Cube.js schema folder'
    });

    if (!schemaPath?.[0]) {
        return;
    }

    vscode.window.showInformationMessage(`Importing from Cube.js: ${schemaPath[0].fsPath}`);
    // Implementation would call cube_compatibility
}
