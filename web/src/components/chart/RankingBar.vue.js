import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);
const props = withDefaults(defineProps(), { height: 400 });
const el = ref(null);
let chart = null;
const colorFn = computed(() => props.color || ((v) => (v >= 0 ? '#dc2626' : '#16a34a')));
const fmt = computed(() => props.formatter || ((v) => v.toFixed(2)));
function render() {
    if (!chart)
        return;
    const cleaned = props.items.filter(i => i.value !== null);
    const labels = cleaned.map(i => i.label);
    const values = cleaned.map(i => i.value);
    chart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 100, right: 60, top: 10, bottom: 30 },
        xAxis: { type: 'value', axisLabel: { formatter: (v) => fmt.value(v) } },
        yAxis: {
            type: 'category',
            data: labels,
            inverse: true,
            axisLabel: { fontSize: 12 },
        },
        series: [
            {
                type: 'bar',
                data: values.map(v => ({ value: v, itemStyle: { color: colorFn.value(v) } })),
                label: {
                    show: true,
                    position: 'right',
                    formatter: (p) => fmt.value(p.value),
                    fontSize: 11,
                },
            },
        ],
    });
}
onMounted(() => {
    chart = echarts.init(el.value);
    render();
    window.addEventListener('resize', resize);
});
onBeforeUnmount(() => {
    window.removeEventListener('resize', resize);
    chart?.dispose();
    chart = null;
});
function resize() {
    chart?.resize();
}
watch(() => props.items, () => render(), { deep: true });
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_withDefaultsArg = (function (t) { return t; })({ height: 400 });
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ref: "el",
    ...{ class: "echart" },
    ...{ style: ({ height: __VLS_ctx.height + 'px' }) },
});
/** @type {typeof __VLS_ctx.el} */ ;
/** @type {__VLS_StyleScopedClasses['echart']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            el: el,
        };
    },
    __typeProps: {},
    props: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
    props: {},
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=RankingBar.vue.js.map