import { onMounted, reactive, ref } from 'vue';
import { analysisApi } from '@/api/analysis';
import { useSessionStore } from '@/stores/session';
import SymbolPicker from '@/components/common/SymbolPicker.vue';
import KLineChart from '@/components/chart/KLineChart.vue';
const session = useSessionStore();
const form = reactive({ symbol: session.symbol });
const overview = ref(null);
const loading = ref(false);
async function load() {
    if (!form.symbol)
        return;
    session.setSymbol(form.symbol);
    loading.value = true;
    try {
        overview.value = await analysisApi.companyOverview(form.symbol);
    }
    catch {
        overview.value = null;
    }
    finally {
        loading.value = false;
    }
}
onMounted(load);
function fmtNum(v) {
    return v == null ? '—' : v.toFixed(2);
}
function fmtPct(v) {
    if (v == null)
        return '—';
    const pct = Math.abs(v) <= 1 ? v * 100 : v;
    return `${pct.toFixed(2)}%`;
}
function fmtCap(v) {
    if (v == null)
        return '—';
    if (v >= 1e8)
        return `${(v / 1e8).toFixed(2)} 亿`;
    if (v >= 1e4)
        return `${(v / 1e4).toFixed(2)} 万`;
    return v.toFixed(2);
}
function pctClass(v) {
    if (v == null)
        return '';
    return v >= 0 ? 'pos' : 'neg';
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "page" },
});
const __VLS_0 = {}.ElCard;
/** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    shadow: "never",
    ...{ class: "search" },
}));
const __VLS_2 = __VLS_1({
    shadow: "never",
    ...{ class: "search" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
/** @type {[typeof SymbolPicker, ]} */ ;
// @ts-ignore
const __VLS_4 = __VLS_asFunctionalComponent(SymbolPicker, new SymbolPicker({
    ...{ 'onSubmit': {} },
    modelValue: (__VLS_ctx.form.symbol),
}));
const __VLS_5 = __VLS_4({
    ...{ 'onSubmit': {} },
    modelValue: (__VLS_ctx.form.symbol),
}, ...__VLS_functionalComponentArgsRest(__VLS_4));
let __VLS_7;
let __VLS_8;
let __VLS_9;
const __VLS_10 = {
    onSubmit: (__VLS_ctx.load)
};
var __VLS_6;
var __VLS_3;
if (!__VLS_ctx.overview && !__VLS_ctx.loading) {
    const __VLS_11 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_12 = __VLS_asFunctionalComponent(__VLS_11, new __VLS_11({
        description: "输入股票代码后点查询",
    }));
    const __VLS_13 = __VLS_12({
        description: "输入股票代码后点查询",
    }, ...__VLS_functionalComponentArgsRest(__VLS_12));
}
if (__VLS_ctx.loading) {
    const __VLS_15 = {}.ElSkeleton;
    /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
    // @ts-ignore
    const __VLS_16 = __VLS_asFunctionalComponent(__VLS_15, new __VLS_15({
        rows: (6),
        animated: true,
    }));
    const __VLS_17 = __VLS_16({
        rows: (6),
        animated: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_16));
}
if (__VLS_ctx.overview) {
    const __VLS_19 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_20 = __VLS_asFunctionalComponent(__VLS_19, new __VLS_19({
        shadow: "never",
        ...{ class: "header" },
    }));
    const __VLS_21 = __VLS_20({
        shadow: "never",
        ...{ class: "header" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_20));
    __VLS_22.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "header-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "title" },
    });
    (__VLS_ctx.overview.info.name);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "muted" },
    });
    (__VLS_ctx.overview.info.symbol);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "sub" },
    });
    (__VLS_ctx.overview.info.industry || '行业未知');
    if (__VLS_ctx.overview.info.listed_date) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.overview.info.listed_date);
    }
    const __VLS_23 = {}.ElDescriptions;
    /** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
    // @ts-ignore
    const __VLS_24 = __VLS_asFunctionalComponent(__VLS_23, new __VLS_23({
        column: (3),
        border: true,
        size: "small",
        ...{ class: "kpis" },
    }));
    const __VLS_25 = __VLS_24({
        column: (3),
        border: true,
        size: "small",
        ...{ class: "kpis" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_24));
    __VLS_26.slots.default;
    const __VLS_27 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_28 = __VLS_asFunctionalComponent(__VLS_27, new __VLS_27({
        label: "总市值",
    }));
    const __VLS_29 = __VLS_28({
        label: "总市值",
    }, ...__VLS_functionalComponentArgsRest(__VLS_28));
    __VLS_30.slots.default;
    (__VLS_ctx.fmtCap(__VLS_ctx.overview.info.market_cap));
    var __VLS_30;
    const __VLS_31 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_32 = __VLS_asFunctionalComponent(__VLS_31, new __VLS_31({
        label: "流通市值",
    }));
    const __VLS_33 = __VLS_32({
        label: "流通市值",
    }, ...__VLS_functionalComponentArgsRest(__VLS_32));
    __VLS_34.slots.default;
    (__VLS_ctx.fmtCap(__VLS_ctx.overview.info.float_market_cap));
    var __VLS_34;
    const __VLS_35 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_36 = __VLS_asFunctionalComponent(__VLS_35, new __VLS_35({
        label: "PE",
    }));
    const __VLS_37 = __VLS_36({
        label: "PE",
    }, ...__VLS_functionalComponentArgsRest(__VLS_36));
    __VLS_38.slots.default;
    (__VLS_ctx.fmtNum(__VLS_ctx.overview.info.pe));
    var __VLS_38;
    var __VLS_26;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "returns" },
    });
    for (const [v, k] of __VLS_getVForSourceType((__VLS_ctx.overview.returns))) {
        const __VLS_39 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_40 = __VLS_asFunctionalComponent(__VLS_39, new __VLS_39({
            key: (k),
            type: (v >= 0 ? 'danger' : 'success'),
            effect: "plain",
            size: "large",
        }));
        const __VLS_41 = __VLS_40({
            key: (k),
            type: (v >= 0 ? 'danger' : 'success'),
            effect: "plain",
            size: "large",
        }, ...__VLS_functionalComponentArgsRest(__VLS_40));
        __VLS_42.slots.default;
        (k);
        ((v * 100).toFixed(2));
        var __VLS_42;
    }
    var __VLS_22;
    const __VLS_43 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_44 = __VLS_asFunctionalComponent(__VLS_43, new __VLS_43({
        shadow: "never",
    }));
    const __VLS_45 = __VLS_44({
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_44));
    __VLS_46.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_46.slots;
    }
    /** @type {[typeof KLineChart, ]} */ ;
    // @ts-ignore
    const __VLS_47 = __VLS_asFunctionalComponent(KLineChart, new KLineChart({
        kline: (__VLS_ctx.overview.kline),
    }));
    const __VLS_48 = __VLS_47({
        kline: (__VLS_ctx.overview.kline),
    }, ...__VLS_functionalComponentArgsRest(__VLS_47));
    var __VLS_46;
    const __VLS_50 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_51 = __VLS_asFunctionalComponent(__VLS_50, new __VLS_50({
        shadow: "never",
    }));
    const __VLS_52 = __VLS_51({
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_51));
    __VLS_53.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_53.slots;
    }
    const __VLS_54 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_55 = __VLS_asFunctionalComponent(__VLS_54, new __VLS_54({
        data: (__VLS_ctx.overview.financials),
        stripe: true,
        size: "small",
    }));
    const __VLS_56 = __VLS_55({
        data: (__VLS_ctx.overview.financials),
        stripe: true,
        size: "small",
    }, ...__VLS_functionalComponentArgsRest(__VLS_55));
    __VLS_57.slots.default;
    const __VLS_58 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_59 = __VLS_asFunctionalComponent(__VLS_58, new __VLS_58({
        prop: "period",
        label: "期间",
        width: "120",
    }));
    const __VLS_60 = __VLS_59({
        prop: "period",
        label: "期间",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_59));
    const __VLS_62 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_63 = __VLS_asFunctionalComponent(__VLS_62, new __VLS_62({
        label: "ROE",
        align: "right",
    }));
    const __VLS_64 = __VLS_63({
        label: "ROE",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_63));
    __VLS_65.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_65.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtPct(row.roe));
    }
    var __VLS_65;
    const __VLS_66 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_67 = __VLS_asFunctionalComponent(__VLS_66, new __VLS_66({
        label: "毛利率",
        align: "right",
    }));
    const __VLS_68 = __VLS_67({
        label: "毛利率",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_67));
    __VLS_69.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_69.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtPct(row.gross_margin));
    }
    var __VLS_69;
    const __VLS_70 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_71 = __VLS_asFunctionalComponent(__VLS_70, new __VLS_70({
        label: "净利率",
        align: "right",
    }));
    const __VLS_72 = __VLS_71({
        label: "净利率",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_71));
    __VLS_73.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_73.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtPct(row.net_margin));
    }
    var __VLS_73;
    const __VLS_74 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_75 = __VLS_asFunctionalComponent(__VLS_74, new __VLS_74({
        label: "营收",
        align: "right",
    }));
    const __VLS_76 = __VLS_75({
        label: "营收",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_75));
    __VLS_77.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_77.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtCap(row.revenue));
    }
    var __VLS_77;
    const __VLS_78 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_79 = __VLS_asFunctionalComponent(__VLS_78, new __VLS_78({
        label: "营收同比",
        align: "right",
    }));
    const __VLS_80 = __VLS_79({
        label: "营收同比",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_79));
    __VLS_81.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_81.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: (__VLS_ctx.pctClass(row.revenue_yoy)) },
        });
        (__VLS_ctx.fmtPct(row.revenue_yoy));
    }
    var __VLS_81;
    const __VLS_82 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_83 = __VLS_asFunctionalComponent(__VLS_82, new __VLS_82({
        label: "净利润",
        align: "right",
    }));
    const __VLS_84 = __VLS_83({
        label: "净利润",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_83));
    __VLS_85.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_85.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtCap(row.net_income));
    }
    var __VLS_85;
    const __VLS_86 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_87 = __VLS_asFunctionalComponent(__VLS_86, new __VLS_86({
        label: "净利同比",
        align: "right",
    }));
    const __VLS_88 = __VLS_87({
        label: "净利同比",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_87));
    __VLS_89.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_89.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: (__VLS_ctx.pctClass(row.net_income_yoy)) },
        });
        (__VLS_ctx.fmtPct(row.net_income_yoy));
    }
    var __VLS_89;
    const __VLS_90 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_91 = __VLS_asFunctionalComponent(__VLS_90, new __VLS_90({
        label: "资产负债率",
        align: "right",
    }));
    const __VLS_92 = __VLS_91({
        label: "资产负债率",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_91));
    __VLS_93.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_93.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtPct(row.debt_ratio));
    }
    var __VLS_93;
    var __VLS_57;
    var __VLS_53;
}
/** @type {__VLS_StyleScopedClasses['page']} */ ;
/** @type {__VLS_StyleScopedClasses['search']} */ ;
/** @type {__VLS_StyleScopedClasses['header']} */ ;
/** @type {__VLS_StyleScopedClasses['header-row']} */ ;
/** @type {__VLS_StyleScopedClasses['title']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['sub']} */ ;
/** @type {__VLS_StyleScopedClasses['kpis']} */ ;
/** @type {__VLS_StyleScopedClasses['returns']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            SymbolPicker: SymbolPicker,
            KLineChart: KLineChart,
            form: form,
            overview: overview,
            loading: loading,
            load: load,
            fmtNum: fmtNum,
            fmtPct: fmtPct,
            fmtCap: fmtCap,
            pctClass: pctClass,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=Index.vue.js.map