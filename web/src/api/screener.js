import http from './client';
export const screenerApi = {
    submit(req) {
        return http.post('/screeners', req).then(r => r.data);
    },
    get(jobId) {
        return http.get(`/screeners/${jobId}`).then(r => r.data);
    },
    list() {
        return http.get('/screeners').then(r => r.data);
    },
    result(jobId) {
        return http.get(`/screeners/${jobId}/result`).then(r => r.data);
    },
    cancel(jobId) {
        return http.delete(`/screeners/${jobId}`).then(r => r.data);
    },
    watch(jobId, onUpdate) {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${location.host}/api/screeners/${jobId}/ws`);
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
    listRules() {
        return http.get('/screeners/rules').then(r => r.data);
    },
};
//# sourceMappingURL=screener.js.map