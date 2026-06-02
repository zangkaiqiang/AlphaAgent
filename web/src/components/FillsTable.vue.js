import { computed } from 'vue';
import dayjs from 'dayjs';
const props = defineProps();
const rows = computed(() => props.fills.map(f => ({
    ...f,
    timestamp: dayjs(f.timestamp).format('YYYY-MM-DD HH:mm'),
})));
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.ElTable;
/** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    data: (__VLS_ctx.rows),
    stripe: true,
    size: "small",
    maxHeight: "320",
}));
const __VLS_2 = __VLS_1({
    data: (__VLS_ctx.rows),
    stripe: true,
    size: "small",
    maxHeight: "320",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
const __VLS_5 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    prop: "timestamp",
    label: "时间",
    width: "170",
}));
const __VLS_7 = __VLS_6({
    prop: "timestamp",
    label: "时间",
    width: "170",
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
const __VLS_9 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
    prop: "symbol",
    label: "代码",
    width: "100",
}));
const __VLS_11 = __VLS_10({
    prop: "symbol",
    label: "代码",
    width: "100",
}, ...__VLS_functionalComponentArgsRest(__VLS_10));
const __VLS_13 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
    label: "方向",
    width: "80",
}));
const __VLS_15 = __VLS_14({
    label: "方向",
    width: "80",
}, ...__VLS_functionalComponentArgsRest(__VLS_14));
__VLS_16.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_16.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    const __VLS_17 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
        type: (row.side === 'BUY' ? 'danger' : 'success'),
        size: "small",
    }));
    const __VLS_19 = __VLS_18({
        type: (row.side === 'BUY' ? 'danger' : 'success'),
        size: "small",
    }, ...__VLS_functionalComponentArgsRest(__VLS_18));
    __VLS_20.slots.default;
    (row.side === 'BUY' ? '买入' : '卖出');
    var __VLS_20;
}
var __VLS_16;
const __VLS_21 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
    prop: "quantity",
    label: "数量",
    width: "100",
    align: "right",
}));
const __VLS_23 = __VLS_22({
    prop: "quantity",
    label: "数量",
    width: "100",
    align: "right",
}, ...__VLS_functionalComponentArgsRest(__VLS_22));
const __VLS_25 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_26 = __VLS_asFunctionalComponent(__VLS_25, new __VLS_25({
    label: "成交价",
    width: "100",
    align: "right",
}));
const __VLS_27 = __VLS_26({
    label: "成交价",
    width: "100",
    align: "right",
}, ...__VLS_functionalComponentArgsRest(__VLS_26));
__VLS_28.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_28.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    (row.fill_price.toFixed(3));
}
var __VLS_28;
const __VLS_29 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({
    label: "佣金",
    width: "100",
    align: "right",
}));
const __VLS_31 = __VLS_30({
    label: "佣金",
    width: "100",
    align: "right",
}, ...__VLS_functionalComponentArgsRest(__VLS_30));
__VLS_32.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_32.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    (row.commission.toFixed(2));
}
var __VLS_32;
const __VLS_33 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_34 = __VLS_asFunctionalComponent(__VLS_33, new __VLS_33({
    label: "印花税",
    width: "100",
    align: "right",
}));
const __VLS_35 = __VLS_34({
    label: "印花税",
    width: "100",
    align: "right",
}, ...__VLS_functionalComponentArgsRest(__VLS_34));
__VLS_36.slots.default;
{
    const { default: __VLS_thisSlot } = __VLS_36.slots;
    const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
    (row.stamp_tax.toFixed(2));
}
var __VLS_36;
const __VLS_37 = {}.ElTableColumn;
/** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
// @ts-ignore
const __VLS_38 = __VLS_asFunctionalComponent(__VLS_37, new __VLS_37({
    prop: "strategy_id",
    label: "策略",
}));
const __VLS_39 = __VLS_38({
    prop: "strategy_id",
    label: "策略",
}, ...__VLS_functionalComponentArgsRest(__VLS_38));
var __VLS_3;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            rows: rows,
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
//# sourceMappingURL=FillsTable.vue.js.map