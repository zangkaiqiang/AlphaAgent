import http from './client';
export const backtestApi = {
    submit(req) {
        return http.post('/backtests', req).then(r => r.data);
    },
    get(jobId) {
        return http.get(`/backtests/${jobId}`).then(r => r.data);
    },
    list() {
        return http.get('/backtests').then(r => r.data);
    },
    result(jobId) {
        return http.get(`/backtests/${jobId}/result`).then(r => r.data);
    },
    cancel(jobId) {
        return http.delete(`/backtests/${jobId}`).then(r => r.data);
    },
    watch(jobId, onUpdate) {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${location.host}/api/backtests/${jobId}/ws`);
        ws.onmessage = (ev) => {
            try {
                onUpdate(JSON.parse(ev.data));
            }
            catch {
                // ignore non-JSON frames
            }
        };
        return ws;
    },
};
//# sourceMappingURL=backtest.js.map