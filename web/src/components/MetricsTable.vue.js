import { computed } from 'vue';
const props = defineProps();
function pct(x, digits = 2) {
    return `${(x * 100).toFixed(digits)}%`;
}
function num(x, digits = 2) {
    if (!isFinite(x))
        return '∞';
    return x.toFixed(digits);
}
const items = computed(() => {
    const p = props.perf;
    return [
        { label: '总收益率', value: pct(p.total_return), cls: p.total_return >= 0 ? 'pos' : 'neg' },
        { label: '年化收益', value: pct(p.annualized_return), cls: p.annualized_return >= 0 ? 'pos' : 'neg' },
        { label: '年化波动', value: pct(p.annualized_volatility) },
        { label: 'Sharpe', value: num(p.sharpe), cls: p.sharpe >= 1 ? 'pos' : '' },
        { label: 'Sortino', value: num(p.sortino) },
        { label: '最大回撤', value: pct(p.max_drawdown), cls: 'neg' },
        { label: 'Calmar', value: num(p.calmar) },
        { label: '交易次数', value: p.trades.toString() },
        { label: '胜率', value: pct(p.win_rate) },
        { label: '平均盈利', value: num(p.avg_win), cls: 'pos' },
        { label: '平均亏损', value: num(p.avg_loss), cls: 'neg' },
        { label: '盈利因子', value: num(p.profit_factor) },
        { label: '总盈亏', value: num(p.total_pnl), cls: p.total_pnl >= 0 ? 'pos' : 'neg' },
    ];
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
const __VLS_0 = {}.ElDescriptions;
/** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    column: (3),
    border: true,
}));
const __VLS_2 = __VLS_1({
    column: (3),
    border: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
for (const [m] of __VLS_getVForSourceType((__VLS_ctx.items))) {
    const __VLS_5 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
        key: (m.label),
        label: (m.label),
    }));
    const __VLS_7 = __VLS_6({
        key: (m.label),
        label: (m.label),
    }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    __VLS_8.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: (m.cls) },
    });
    (m.value);
    var __VLS_8;
}
var __VLS_3;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            items: items,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=MetricsTable.vue.js.map