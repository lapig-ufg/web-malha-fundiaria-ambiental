const fs = require('fs');
const path = require('path');

module.exports = function(app) {
    const logFilePath = path.join(app.config.appRoot.path, 'migration_behavior.log');

    return function(req, res, next) {
        const timestamp = new Date().toISOString();
        const { method, url, body, query } = req;

        if (!url.includes('/api') && !url.includes('/service')) {
            return next();
        }

        const oldSend = res.send;
        res.send = function(data) {
            let logEntry = `\n[${timestamp}] === REQUEST ===\n`;
            logEntry += `${method} ${url}\n`;
            if (Object.keys(query).length) logEntry += `Query: ${JSON.stringify(query, null, 2)}\n`;
            if (req.params && Object.keys(req.params).length) logEntry += `Params: ${JSON.stringify(req.params, null, 2)}\n`;
            if (method !== 'GET' && body && Object.keys(body).length) {
                logEntry += `Payload: ${JSON.stringify(body, null, 2)}\n`;
            }
            
            logEntry += `[${timestamp}] === RESPONSE [Status: ${res.statusCode}] ===\n`;
            try {
                if (data) {
                    const responseData = typeof data === 'string' ? JSON.parse(data) : data;
                    const logData = JSON.stringify(responseData, null, 2);
                    if (logData.length > 10000) {
                        logEntry += `Response (truncated): ${logData.substring(0, 10000)}...\n`;
                    } else {
                        logEntry += `Response: ${logData}\n`;
                    }
                } else {
                    logEntry += `Response: (empty)\n`;
                }
            } catch (e) {
                if (typeof data === 'string') {
                    logEntry += `Response (text): ${data.substring(0, 500)}${data.length > 500 ? '...' : ''}\n`;
                } else {
                    logEntry += `Response (buffer/other): ${typeof data}\n`;
                }
            }
            logEntry += `==================================================\n`;
            
            // Log to console
            console.log(logEntry);

            // Log to file
            try {
                fs.appendFileSync(logFilePath, logEntry);
            } catch (err) {
                console.error('Failed to write to migration log file:', err);
            }
            
            return oldSend.apply(res, arguments);
        };

        next();
    };
};
