import { defineStore } from 'pinia';
import { ref } from 'vue';
import { strategiesApi } from '@/api/strategies';
export const useStrategiesStore = defineStore('strategies', () => {
    const list = ref([]);
    const loaded = ref(false);
    async function load(force = false) {
        if (loaded.value && !force)
            return;
        list.value = await strategiesApi.list();
        loaded.value = true;
    }
    return { list, loaded, load };
});
//# sourceMappingURL=strategies.js.map