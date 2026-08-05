// DevFlow Fullstack - VS Code Extension 源码
// 提供代码审查、安全扫描、测试生成、文档生成等 10 个命令
import * as vscode from 'vscode';
import * as child_process from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

interface DevFlowConfig {
    pythonPath: string;
    scriptsPath: string;
    outputFormat: string;
    autoReview: boolean;
}

// 获取用户配置
function getConfig(): DevFlowConfig {
    const config = vscode.workspace.getConfiguration('devflow');
    return {
        pythonPath: config.get<string>('pythonPath', 'python'),
        scriptsPath: config.get<string>('scriptsPath', ''),
        outputFormat: config.get<string>('outputFormat', 'text'),
        autoReview: config.get<boolean>('autoReview', false)
    };
}

// 获取 DevFlow 脚本路径
function getScriptsPath(): string {
    const config = getConfig();
    if (config.scriptsPath) {
        return config.scriptsPath;
    }
    // 开发模式：项目根目录下的 scripts/（out/ 的上一级是 vscode-extension，再上一级是项目根）
    const repoScripts = path.join(__dirname, '..', '..', 'scripts');
    if (fs.existsSync(repoScripts)) {
        return repoScripts;
    }
    // 打包模式：扩展内自带的 scripts/（若随 .vsix 一起打包）
    const bundled = path.join(__dirname, '..', 'scripts');
    if (fs.existsSync(bundled)) {
        return bundled;
    }
    return '';
}

// 执行 Python 脚本（使用参数数组，避免路径含空格时出错）
function runScript(scriptName: string, argsList: string[] = []): Promise<string> {
    const config = getConfig();
    const scriptsPath = getScriptsPath();
    const scriptPath = path.join(scriptsPath, scriptName);

    return new Promise((resolve, reject) => {
        if (!fs.existsSync(scriptPath)) {
            reject(new Error(
                `找不到 DevFlow 脚本: ${scriptPath}\n` +
                `请在 VS Code 设置中配置 devflow.scriptsPath，指向项目根目录下的 scripts/ 文件夹。`
            ));
            return;
        }
        child_process.execFile(config.pythonPath, [scriptPath, ...argsList], { encoding: 'utf-8' }, (error, stdout, stderr) => {
            // exit code 1 通常表示发现问题，不是错误
            if (error && error.code !== 1) {
                reject(new Error(stderr || error.message));
            } else {
                resolve(stdout || stderr);
            }
        });
    });
}

// 获取当前打开的文件路径
function getCurrentFilePath(): string | undefined {
    const editor = vscode.window.activeTextEditor;
    return editor ? editor.document.fileName : undefined;
}

// 显示输出面板
function showOutput(content: string, title: string = 'DevFlow'): void {
    const panel = vscode.window.createOutputChannel(title);
    panel.append(content);
    panel.show();
}

// 显示 Webview 面板（用于富文本输出）
function showWebview(content: string, title: string): void {
    const panel = vscode.window.createWebviewPanel(
        'devflowOutput',
        title,
        vscode.ViewColumn.Beside,
        { enableScripts: false }
    );
    const escaped = content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    panel.webview.html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        code { font-family: 'Consolas', 'Monaco', monospace; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
        .success { color: #28a745; }
    </style>
</head>
<body>
    <pre><code>${escaped}</code></pre>
</body>
</html>`;
}

// 命令：代码审查
async function reviewCode(): Promise<void> {
    const filePath = getCurrentFilePath();
    if (!filePath) {
        vscode.window.showErrorMessage('No file open');
        return;
    }
    try {
        vscode.window.showInformationMessage('Running code review...');
        const result = await runScript('review.py', ['--file', filePath, '--mode', 'all']);
        showOutput(result, 'DevFlow Code Review');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Review failed: ${error.message}`);
    }
}

// 命令：安全扫描
async function reviewSecurity(): Promise<void> {
    const filePath = getCurrentFilePath();
    if (!filePath) {
        vscode.window.showErrorMessage('No file open');
        return;
    }
    try {
        vscode.window.showInformationMessage('Running security scan...');
        const result = await runScript('review.py', ['--file', filePath, '--mode', 'security']);
        showOutput(result, 'DevFlow Security Scan');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Security scan failed: ${error.message}`);
    }
}

// 命令：解释代码
async function explainCode(): Promise<void> {
    const filePath = getCurrentFilePath();
    if (!filePath) {
        vscode.window.showErrorMessage('No file open');
        return;
    }
    try {
        vscode.window.showInformationMessage('Analyzing code...');
        const result = await runScript('explain.py', ['--file', filePath]);
        showWebview(result, 'DevFlow Code Explanation');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Explanation failed: ${error.message}`);
    }
}

// 命令：生成测试
async function generateTests(): Promise<void> {
    const filePath = getCurrentFilePath();
    if (!filePath) {
        vscode.window.showErrorMessage('No file open');
        return;
    }
    try {
        vscode.window.showInformationMessage('Generating tests...');
        const result = await runScript('testgen.py', ['--file', filePath, '--framework', 'pytest']);
        showOutput(result, 'DevFlow Test Generator');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Test generation failed: ${error.message}`);
    }
}

// 命令：生成文档
async function generateDocs(): Promise<void> {
    const filePath = getCurrentFilePath();
    if (!filePath) {
        vscode.window.showErrorMessage('No file open');
        return;
    }
    try {
        vscode.window.showInformationMessage('Generating documentation...');
        const result = await runScript('docgen.py', ['--file', filePath, '--mode', 'all']);
        showOutput(result, 'DevFlow Documentation');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Documentation generation failed: ${error.message}`);
    }
}

// 命令：格式化检查
async function formatCode(): Promise<void> {
    const filePath = getCurrentFilePath();
    if (!filePath) {
        vscode.window.showErrorMessage('No file open');
        return;
    }
    try {
        vscode.window.showInformationMessage('Checking formatting...');
        const result = await runScript('formatter.py', ['--file', filePath, '--check']);
        showOutput(result, 'DevFlow Code Formatter');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Format check failed: ${error.message}`);
    }
}

// 命令：检查依赖漏洞
async function checkDeps(): Promise<void> {
    try {
        vscode.window.showInformationMessage('Checking dependencies...');
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace open');
            return;
        }
        const dir = workspaceFolders[0].uri.fsPath;
        const result = await runScript('deps-scan.py', ['--dir', dir]);
        showOutput(result, 'DevFlow Dependency Check');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Dependency check failed: ${error.message}`);
    }
}

// 命令：生成 Changelog
async function generateChangelog(): Promise<void> {
    try {
        vscode.window.showInformationMessage('Generating changelog...');
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace open');
            return;
        }
        const dir = workspaceFolders[0].uri.fsPath;
        const result = await runScript('changelog.py', ['--dir', dir]);
        showOutput(result, 'DevFlow Changelog');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Changelog generation failed: ${error.message}`);
    }
}

// 命令：显示仪表盘
async function showDashboard(): Promise<void> {
    try {
        vscode.window.showInformationMessage('Generating dashboard...');
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace open');
            return;
        }
        const dir = workspaceFolders[0].uri.fsPath;
        const result = await runScript('dashboard.py', ['--dir', dir, '--format', 'json']);
        showWebview(result, 'DevFlow Dashboard');
    } catch (error: any) {
        vscode.window.showErrorMessage(`Dashboard failed: ${error.message}`);
    }
}

// 命令：生成 Docker Compose
async function generateDockerCompose(): Promise<void> {
    try {
        const options = ['web', 'fullstack', 'python', 'django', 'flask', 'node', 'go'];
        const selected = await vscode.window.showQuickPick(options, {
            placeHolder: 'Select architecture type'
        });
        if (selected) {
            vscode.window.showInformationMessage('Generating Docker Compose...');
            const result = await runScript('docker-compose-gen.py', ['--type', selected]);
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders) {
                const filePath = path.join(workspaceFolders[0].uri.fsPath, 'docker-compose.yml');
                fs.writeFileSync(filePath, result);
                vscode.window.showInformationMessage(`Docker Compose saved to ${filePath}`);
            }
        }
    } catch (error: any) {
        vscode.window.showErrorMessage(`Docker Compose generation failed: ${error.message}`);
    }
}

// 扩展激活入口
export function activate(context: vscode.ExtensionContext): void {
    console.log('DevFlow Fullstack is now active!');

    // 注册命令
    const commands = [
        vscode.commands.registerCommand('devflow.review', reviewCode),
        vscode.commands.registerCommand('devflow.reviewSecurity', reviewSecurity),
        vscode.commands.registerCommand('devflow.explain', explainCode),
        vscode.commands.registerCommand('devflow.generateTests', generateTests),
        vscode.commands.registerCommand('devflow.generateDocs', generateDocs),
        vscode.commands.registerCommand('devflow.formatCode', formatCode),
        vscode.commands.registerCommand('devflow.checkDeps', checkDeps),
        vscode.commands.registerCommand('devflow.generateChangelog', generateChangelog),
        vscode.commands.registerCommand('devflow.showDashboard', showDashboard),
        vscode.commands.registerCommand('devflow.generateDockerCompose', generateDockerCompose)
    ];

    commands.forEach(cmd => context.subscriptions.push(cmd));

    // 自动审查功能（保存时触发）
    if (getConfig().autoReview) {
        const disposable = vscode.workspace.onDidSaveTextDocument(async (document) => {
            const ext = path.extname(document.fileName);
            if (['.py', '.js', '.ts', '.jsx', '.tsx'].includes(ext)) {
                try {
                    const result = await runScript('review.py', ['--file', document.fileName, '--mode', 'security']);
                    if (result.includes('[L4]') || result.includes('[CRITICAL]')) {
                        vscode.window.showWarningMessage('DevFlow: Critical issues found!');
                    }
                } catch (error) {
                    // 静默失败
                }
            }
        });
        context.subscriptions.push(disposable);
    }
}

// 扩展停用入口
export function deactivate(): void {}
