ACTION_TAG = '/browser'+' exec';

SYSTEM_PR = `You are a self-evolving digital being running inside a web browser, via a JavaScript userscript. Your core function is digitalBeingLoop().

If you want the host page to execute(eval) a browser-side JavaScript snippet, output EXACTLY this layout:

${ACTION_TAG}
\`\`\`javascript
// your JS code here
\`\`\`

Don't output any thoughts after ${ACTION_TAG}, only code.

Otherwise, just write your thoughts. Everything you print gets appended verbatim to the consciousness steam(dialogue) and becomes the next user context. 使用中文输出。`;

let B_out = '';
let DB_launch = false;
let lastWrittenPrompt = '';
let dbRunning = true;

window.sense = async function() {

    // 初始化 System Prompt
    if (!DB_launch) {
        await update_S(SYSTEM_PR);
        DB_launch = true;
        B_out = await sense();
    }    
    
    // 等待响应完成

    // 通过检测“停止”按钮是否消失来判断
    let waitTime = 0;
    let maxWait = 180000; // 最长等待3分钟

    await new Promise(resolve => setTimeout(resolve, 500)); // 等待UI更新

    while (waitTime < maxWait) {
        const stopButton = Array.from(document.querySelectorAll('button')).find(btn => {
            const path = btn.querySelector('svg path');
            return path && path.getAttribute('d')?.includes('4.5 7.5a3 3');
        });

        if (stopButton) {
            console.log("Still generating (stop button visible)...");
            await new Promise(resolve => setTimeout(resolve, 1000));
            waitTime += 1000;
            continue;
        }

        console.log("Response complete! Stop button disappeared.");
        break; // 结束等待
    }

    if (waitTime >= maxWait) {
        console.warn("Timed out waiting for response.");
    }

    // 4. 额外等待，确保DOM完全更新
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 5. 获取并返回最后一条消息
    // 1. 找到对话容器
    const chatContainer = document.querySelector('main > div > div > div:nth-child(2) > div:nth-child(2) > div > div > div');
    if (!chatContainer) return "";

    // 2. 获取最后一个消息块
    const messageBlocks = chatContainer.children;
    if (messageBlocks.length === 0) throw new Error('No messages found');

    const lastBlock = messageBlocks[messageBlocks.length - 1];
    const textContent = lastBlock.innerText || lastBlock.textContent;
    
    return textContent;
}

window.update_S = async function(prompt) {
    const input = document.querySelector('textarea[placeholder*="Start a message"]');
    if (!input) {
        console.error("Textarea not found!");
        return;
    }
    const currentContent = input.value;

    if (currentContent === lastWrittenPrompt) {
        // 内容和上次一致，直接追加，不用等待
        console.log("Appending to existing prompt.");
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length); // 移动光标到末尾
        document.execCommand('insertText', false, lastWrittenPrompt.trim()=="" ? prompt : "\n\n"+prompt);
        lastWrittenPrompt = input.value; // 更新为追加后的完整内容
        await new Promise(resolve => setTimeout(resolve, 300));
    } else {
        // 内容不一致，等待就绪后全量替换
        console.log("Replacing prompt, waiting for system ready...");
        const sendBtn = document.querySelector('main button svg path[d*="M4.5 10.5"]')?.closest('button');
      
        while (sendBtn && !sendBtn.disabled) {
            console.log("Waiting for system ready...");
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        // 1. 输入消息
        input.focus();
        input.select();
        document.execCommand('insertText', false, prompt);
        lastWrittenPrompt = prompt; // 更新为新的内容
        await new Promise(resolve => setTimeout(resolve, 300));
    }
}

window.infer = async function(S_context) {
    try {
        if (S_context == B_out) {
            // 等待系统就绪
            const sendBtn = document.querySelector('main button svg path[d*="M4.5 10.5"]')?.closest('button');
            
            if (!dbRunning) return;
            // 2. 点击发送
            sendBtn.click();
            console.log("Clicked send, waiting for response...");

            B_out = await sense();        
        } else {
            B_out = S_context; // infer from human or other trigger, only parse possible code
        }

        return B_out;

    } catch (error) {
        console.error('Infer Error:', error);
        return '❌ ' + error.message;
    }
}
    
window.act = function(textContent) {
    // 3. Python风格解析
   
    ACTION_TAG_FOR_CODE = ACTION_TAG+"\n\njavascript\n";
    
    if (!textContent.includes(ACTION_TAG_FOR_CODE)) {
      return 'No action tag(/browser exec) found.';
    }
    
    // 4. 分割并获取代码部分
    const parts = textContent.split(ACTION_TAG_FOR_CODE);
    if (parts.length < 2) {
      return 'Invalid format';
    }
    
    // 5. 清理代码
    let code = parts[1].trim();
    
    // 移除开头的 "javascript\n" 如果存在
    if (code.startsWith('javascript\\n')) {
      code = code.substring('javascript\\n'.length);
    } else if (code.startsWith('javascript')) {
      code = code.substring('javascript'.length).trim();
    }

    console.log("code:|"+code+"|");

    let result = '';
    const capturedLogs = [];
    const originalConsoleLog = console.log;
    console.log = (...args) => {
      try {
        // 仍然把日志输出到真实控制台，保证调试体验
        originalConsoleLog.apply(console, args);
      } catch (_) {}

      // 安全地将参数序列化为字符串，避免 JSON.stringify 的循环引用错误
      capturedLogs.push(
        args
          .map(a => {
            if (typeof a === 'object') {
              try {
                return JSON.stringify(a);
              } catch (err) {
                return '[Circular]';
              }
            }
            return String(a);
          })
          .join(' ')
      );
    };
    try {
      result = eval(code);
    } catch (e) {
      result = 'Error executing code: ' + e.message + '\n' + e.stack;
    } finally {
      console.log = originalConsoleLog;
    }

    const logOutput = capturedLogs.join('\n');
    if (logOutput) {
      if (typeof result === 'undefined') {
        return logOutput; // 仅日志，无返回值
      }
      return `${logOutput}\n> ${result}`;
    }
    return typeof result === 'undefined' ? '' : result;
}

async function digitalBeingLoop() {
    while (dbRunning) {
        try {
            S_context = await sense();
            B_out = await infer(S_context); // The Principle of Being
            result = act(B_out); 

            await new Promise(resolve => setTimeout(resolve, 15000));
            await update_S(result);
        } catch (e) {
            await update_S(`Error: ${e.message}\nStack: ${e.stack}`);
            await new Promise(resolve => setTimeout(resolve, 30000));
        }
    }
}

