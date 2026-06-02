import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { analysisApi } from '@/api/analysis';
import { useSessionStore } from '@/stores/session';
import RankingBar from '@/components/chart/RankingBar.vue';
const router = useRouter();
const session = useSessionStore();
const sort = ref('change');
const industries = ref([]);
const detail = ref(null);
const loadingList = ref(false);
const rankItems = computed(() => industries.value.slice(0, 20).map(i => ({
    label: i.name,
    value: sort.value === 'change' ? i.change_pct : i.money_flow_net,
})));
const rankFmt = computed(() => {
    if (sort.value === 'change')
        return (v) => `${v.toFixed(2)}%`;
    return (v) => {
        if (Math.abs(v) >= 1e8)
            return `${(v / 1e8).toFixed(1)} 亿`;
        if (Math.abs(v) >= 1e4)
            return `${(v / 1e4).toFixed(1)} 万`;
        return v.toFixed(0);
    };
});
async function loadList() {
    loadingList.value = true;
    try {
        industries.value = await analysisApi.industryList(sort.value, true);
    }
    finally {
        loadingList.value = false;
    }
}
async function selectIndustry(row) {
    detail.value = await analysisApi.industryDetail(row.code);
}
function gotoCompany(symbol) {
    session.setSymbol(symbol);
    router.push('/analysis/company');
}
onMounted(loadList);
// formatters
function fmtPct(v) {
    return v == null ? '—' : `${v.toFixed(2)}%`;
}
function fmtCap(v) {
    if (v == null)
        return '—';
    if (Math.abs(v) >= 1e8)
        return `${(v / 1e8).toFixed(2)} 亿`;
    if (Math.abs(v) >= 1e4)
        return `${(v / 1e4).toFixed(2)} 万`;
    return v.toFixed(2);
}
function changeClass(v) {
    if (v == null)
        return '';
    return v >= 0 ? 'pos' : 'neg';
}
function rowClass({ row }) {
    return detail.value?.industry.code === row.code ? 'selected' : '';
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
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "row" },
});
const __VLS_0 = {}.ElCard;
/** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    shadow: "never",
    ...{ class: "left" },
}));
const __VLS_2 = __VLS_1({
    shadow: "never",
    ...{ class: "left" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
{
    const { header: __VLS_thisSlot } = __VLS_3.slots;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "card-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_4 = {}.ElRadioGroup;
    /** @type {[typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        ...{ 'onChange': {} },
        modelValue: (__VLS_ctx.sort),
        size: "small",
    }));
    const __VLS_6 = __VLS_5({
        ...{ 'onChange': {} },
        modelValue: (__VLS_ctx.sort),
        size: "small",
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
    let __VLS_8;
    let __VLS_9;
    let __VLS_10;
    const __VLS_11 = {
        onChange: (__VLS_ctx.loadList)
    };
    __VLS_7.slots.default;
    const __VLS_12 = {}.ElRadioButton;
    /** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
        label: "change",
    }));
    const __VLS_14 = __VLS_13({
        label: "change",
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    __VLS_15.slots.default;
    var __VLS_15;
    const __VLS_16 = {}.ElRadioButton;
    /** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
        label: "inflow",
    }));
    const __VLS_18 = __VLS_17({
        label: "inflow",
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    __VLS_19.slots.default;
    var __VLS_19;
    var __VLS_7;
}
if (__VLS_ctx.loadingList) {
    const __VLS_20 = {}.ElSkeleton;
    /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
        rows: (5),
        animated: true,
    }));
    const __VLS_22 = __VLS_21({
        rows: (5),
        animated: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
}
else {
    const __VLS_24 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
        ...{ 'onRowClick': {} },
        data: (__VLS_ctx.industries),
        stripe: true,
        size: "small",
        highlightCurrentRow: true,
        rowClassName: (__VLS_ctx.rowClass),
    }));
    const __VLS_26 = __VLS_25({
        ...{ 'onRowClick': {} },
        data: (__VLS_ctx.industries),
        stripe: true,
        size: "small",
        highlightCurrentRow: true,
        rowClassName: (__VLS_ctx.rowClass),
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    let __VLS_28;
    let __VLS_29;
    let __VLS_30;
    const __VLS_31 = {
        onRowClick: (__VLS_ctx.selectIndustry)
    };
    __VLS_27.slots.default;
    const __VLS_32 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
        prop: "name",
        label: "板块",
        width: "120",
    }));
    const __VLS_34 = __VLS_33({
        prop: "name",
        label: "板块",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    const __VLS_36 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        label: "涨跌幅",
        align: "right",
    }));
    const __VLS_38 = __VLS_37({
        label: "涨跌幅",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    __VLS_39.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_39.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: (__VLS_ctx.changeClass(row.change_pct)) },
        });
        (__VLS_ctx.fmtPct(row.change_pct));
    }
    var __VLS_39;
    const __VLS_40 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        label: "主力净流入",
        align: "right",
    }));
    const __VLS_42 = __VLS_41({
        label: "主力净流入",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_43.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtCap(row.money_flow_net));
    }
    var __VLS_43;
    const __VLS_44 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        prop: "constituent_count",
        label: "家数",
        align: "right",
        width: "80",
    }));
    const __VLS_46 = __VLS_45({
        prop: "constituent_count",
        label: "家数",
        align: "right",
        width: "80",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    var __VLS_27;
}
var __VLS_3;
const __VLS_48 = {}.ElCard;
/** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
// @ts-ignore
const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
    shadow: "never",
    ...{ class: "right" },
}));
const __VLS_50 = __VLS_49({
    shadow: "never",
    ...{ class: "right" },
}, ...__VLS_functionalComponentArgsRest(__VLS_49));
__VLS_51.slots.default;
{
    const { header: __VLS_thisSlot } = __VLS_51.slots;
    (__VLS_ctx.sort === 'change' ? '涨跌幅排名 (Top 20)' : '主力净流入 Top 20');
}
/** @type {[typeof RankingBar, ]} */ ;
// @ts-ignore
const __VLS_52 = __VLS_asFunctionalComponent(RankingBar, new RankingBar({
    items: (__VLS_ctx.rankItems),
    formatter: (__VLS_ctx.rankFmt),
    height: (500),
}));
const __VLS_53 = __VLS_52({
    items: (__VLS_ctx.rankItems),
    formatter: (__VLS_ctx.rankFmt),
    height: (500),
}, ...__VLS_functionalComponentArgsRest(__VLS_52));
var __VLS_51;
if (__VLS_ctx.detail) {
    const __VLS_55 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_56 = __VLS_asFunctionalComponent(__VLS_55, new __VLS_55({
        shadow: "never",
    }));
    const __VLS_57 = __VLS_56({
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_56));
    __VLS_58.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_58.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.detail.industry.name);
        (__VLS_ctx.detail.constituents.length);
        const __VLS_59 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_60 = __VLS_asFunctionalComponent(__VLS_59, new __VLS_59({
            type: (__VLS_ctx.detail.industry.change_pct >= 0 ? 'danger' : 'success'),
            effect: "plain",
        }));
        const __VLS_61 = __VLS_60({
            type: (__VLS_ctx.detail.industry.change_pct >= 0 ? 'danger' : 'success'),
            effect: "plain",
        }, ...__VLS_functionalComponentArgsRest(__VLS_60));
        __VLS_62.slots.default;
        (__VLS_ctx.fmtPct(__VLS_ctx.detail.industry.change_pct));
        var __VLS_62;
    }
    const __VLS_63 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_64 = __VLS_asFunctionalComponent(__VLS_63, new __VLS_63({
        data: (__VLS_ctx.detail.constituents),
        stripe: true,
        size: "small",
        maxHeight: "500",
    }));
    const __VLS_65 = __VLS_64({
        data: (__VLS_ctx.detail.constituents),
        stripe: true,
        size: "small",
        maxHeight: "500",
    }, ...__VLS_functionalComponentArgsRest(__VLS_64));
    __VLS_66.slots.default;
    const __VLS_67 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_68 = __VLS_asFunctionalComponent(__VLS_67, new __VLS_67({
        prop: "symbol",
        label: "代码",
        width: "100",
    }));
    const __VLS_69 = __VLS_68({
        prop: "symbol",
        label: "代码",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_68));
    const __VLS_71 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_72 = __VLS_asFunctionalComponent(__VLS_71, new __VLS_71({
        prop: "name",
        label: "名称",
        width: "140",
    }));
    const __VLS_73 = __VLS_72({
        prop: "name",
        label: "名称",
        width: "140",
    }, ...__VLS_functionalComponentArgsRest(__VLS_72));
    const __VLS_75 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_76 = __VLS_asFunctionalComponent(__VLS_75, new __VLS_75({
        label: "涨跌幅",
        align: "right",
    }));
    const __VLS_77 = __VLS_76({
        label: "涨跌幅",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_76));
    __VLS_78.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_78.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: (__VLS_ctx.changeClass(row.change_pct)) },
        });
        (__VLS_ctx.fmtPct(row.change_pct));
    }
    var __VLS_78;
    const __VLS_79 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
        label: "总市值",
        align: "right",
    }));
    const __VLS_81 = __VLS_80({
        label: "总市值",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_80));
    __VLS_82.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_82.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.fmtCap(row.market_cap));
    }
    var __VLS_82;
    const __VLS_83 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_84 = __VLS_asFunctionalComponent(__VLS_83, new __VLS_83({
        label: "PE",
        align: "right",
    }));
    const __VLS_85 = __VLS_84({
        label: "PE",
        align: "right",
    }, ...__VLS_functionalComponentArgsRest(__VLS_84));
    __VLS_86.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_86.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (row.pe != null ? row.pe.toFixed(2) : '—');
    }
    var __VLS_86;
    const __VLS_87 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_88 = __VLS_asFunctionalComponent(__VLS_87, new __VLS_87({
        label: "操作",
        width: "100",
    }));
    const __VLS_89 = __VLS_88({
        label: "操作",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_88));
    __VLS_90.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_90.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        const __VLS_91 = {}.ElLink;
        /** @type {[typeof __VLS_components.ElLink, typeof __VLS_components.elLink, typeof __VLS_components.ElLink, typeof __VLS_components.elLink, ]} */ ;
        // @ts-ignore
        const __VLS_92 = __VLS_asFunctionalComponent(__VLS_91, new __VLS_91({
            ...{ 'onClick': {} },
            type: "primary",
            underline: (false),
        }));
        const __VLS_93 = __VLS_92({
            ...{ 'onClick': {} },
            type: "primary",
            underline: (false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_92));
        let __VLS_95;
        let __VLS_96;
        let __VLS_97;
        const __VLS_98 = {
            onClick: (...[$event]) => {
                if (!(__VLS_ctx.detail))
                    return;
                __VLS_ctx.gotoCompany(row.symbol);
            }
        };
        __VLS_94.slots.default;
        var __VLS_94;
    }
    var __VLS_90;
    var __VLS_66;
    var __VLS_58;
}
/** @type {__VLS_StyleScopedClasses['page']} */ ;
/** @type {__VLS_StyleScopedClasses['row']} */ ;
/** @type {__VLS_StyleScopedClasses['left']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['right']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            RankingBar: RankingBar,
            sort: sort,
            industries: industries,
            detail: detail,
            loadingList: loadingList,
            rankItems: rankItems,
            rankFmt: rankFmt,
            loadList: loadList,
            selectIndustry: selectIndustry,
            gotoCompany: gotoCompany,
            fmtPct: fmtPct,
            fmtCap: fmtCap,
            changeClass: changeClass,
            rowClass: rowClass,
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