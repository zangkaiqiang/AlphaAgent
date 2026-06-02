import { defineStore } from 'pinia';
import { ref } from 'vue';
import dayjs from 'dayjs';
/**
 * Global session state shared across modules:
 *   - the currently selected symbol (drives company analysis page)
 *   - the default date range (drives backtest + research pages)
 *
 * Living here means clicking a stock in industry-analysis can jump to
 * the company page with the selection preserved.
 */
export const useSessionStore = defineStore('session', () => {
    const symbol = ref('600000');
    const dateRange = ref([
        dayjs().subtract(1, 'year').format('YYYY-MM-DD'),
        dayjs().format('YYYY-MM-DD'),
    ]);
    function setSymbol(s) {
        symbol.value = s;
    }
    return { symbol, dateRange, setSymbol };
});
//# sourceMappingURL=session.js.map