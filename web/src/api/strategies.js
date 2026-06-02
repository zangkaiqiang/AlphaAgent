import http from './client';
export const strategiesApi = {
    list() {
        return http.get('/strategies').then(r => r.data);
    },
};
//# sourceMappingURL=strategies.js.map