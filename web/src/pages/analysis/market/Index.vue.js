import { onMounted, ref } from 'vue';
import { analysisApi } from '@/api/analysis';
const snap = ref(null);
const loading = ref(false);
async function load() {
    loading.value = true;
    try {
        snap.value = await analysisApi.marketSnapshot();
    }
    finally {
        loading.value = false;
    }
}
onMounted(load);
function fmtFlow(v) {
    if (v == null)
        return '—';
    const abs = Math.abs(v);
    if (abs >= 1e8)
        return `${(v / 1e8).toFixed(2)} 亿`;
    if (abs >= 1e4)
        return `${(v / 1e4).toFixed(2)} 万`;
    return v.toFixed(2);
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
if (__VLS_ctx.loading) {
    const __VLS_0 = {}.ElSkeleton;
    /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
        rows: (6),
        animated: true,
    }));
    const __VLS_2 = __VLS_1({
        rows: (6),
        animated: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
else if (__VLS_ctx.snap) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "indices" },
    });
    for (const [idx] of __VLS_getVForSourceType((__VLS_ctx.snap.indices))) {
        const __VLS_4 = {}.ElCard;
        /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
        // @ts-ignore
        const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
            key: (idx.code),
            shadow: "never",
            ...{ class: "idx-card" },
        }));
        const __VLS_6 = __VLS_5({
            key: (idx.code),
            shadow: "never",
            ...{ class: "idx-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_5));
        __VLS_7.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "idx-name" },
        });
        (idx.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (idx.code);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "idx-last" },
            ...{ class: (idx.change_pct >= 0 ? 'pos' : 'neg') },
        });
        (idx.last.toFixed(2));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: (idx.change_pct >= 0 ? 'pos' : 'neg') },
        });
        (idx.change_pct >= 0 ? '+' : '');
        (idx.change_pct.toFixed(2));
        var __VLS_7;
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "two-cols" },
    });
    const __VLS_8 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        shadow: "never",
    }));
    const __VLS_10 = __VLS_9({
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    __VLS_11.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_11.slots;
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "breadth" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "breadth-bars" },
    });
    const __VLS_12 = {}.ElTooltip;
    /** @type {[typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, ]} */ ;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
        content: (`上涨 ${__VLS_ctx.snap.breadth.advancers}`),
    }));
    const __VLS_14 = __VLS_13({
        content: (`上涨 ${__VLS_ctx.snap.breadth.advancers}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    __VLS_15.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "bar pos-bg" },
        ...{ style: ({ flex: __VLS_ctx.snap.breadth.advancers ?? 0 }) },
    });
    if ((__VLS_ctx.snap.breadth.advancers ?? 0) > 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.snap.breadth.advancers);
    }
    var __VLS_15;
    const __VLS_16 = {}.ElTooltip;
    /** @type {[typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
        content: (`平盘 ${__VLS_ctx.snap.breadth.unchanged}`),
    }));
    const __VLS_18 = __VLS_17({
        content: (`平盘 ${__VLS_ctx.snap.breadth.unchanged}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    __VLS_19.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "bar neutral-bg" },
        ...{ style: ({ flex: __VLS_ctx.snap.breadth.unchanged ?? 0 }) },
    });
    if ((__VLS_ctx.snap.breadth.unchanged ?? 0) > 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.snap.breadth.unchanged);
    }
    var __VLS_19;
    const __VLS_20 = {}.ElTooltip;
    /** @type {[typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, ]} */ ;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
        content: (`下跌 ${__VLS_ctx.snap.breadth.decliners}`),
    }));
    const __VLS_22 = __VLS_21({
        content: (`下跌 ${__VLS_ctx.snap.breadth.decliners}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    __VLS_23.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "bar neg-bg" },
        ...{ style: ({ flex: __VLS_ctx.snap.breadth.decliners ?? 0 }) },
    });
    if ((__VLS_ctx.snap.breadth.decliners ?? 0) > 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.snap.breadth.decliners);
    }
    var __VLS_23;
    const __VLS_24 = {}.ElDescriptions;
    /** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
        column: (3),
        border: true,
        size: "small",
        ...{ style: {} },
    }));
    const __VLS_26 = __VLS_25({
        column: (3),
        border: true,
        size: "small",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    __VLS_27.slots.default;
    const __VLS_28 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
        label: "上涨",
    }));
    const __VLS_30 = __VLS_29({
        label: "上涨",
    }, ...__VLS_functionalComponentArgsRest(__VLS_29));
    __VLS_31.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "pos" },
    });
    (__VLS_ctx.snap.breadth.advancers ?? '—');
    var __VLS_31;
    const __VLS_32 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
        label: "下跌",
    }));
    const __VLS_34 = __VLS_33({
        label: "下跌",
    }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    __VLS_35.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "neg" },
    });
    (__VLS_ctx.snap.breadth.decliners ?? '—');
    var __VLS_35;
    const __VLS_36 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        label: "平盘",
    }));
    const __VLS_38 = __VLS_37({
        label: "平盘",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    __VLS_39.slots.default;
    (__VLS_ctx.snap.breadth.unchanged ?? '—');
    var __VLS_39;
    const __VLS_40 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        label: "涨停",
    }));
    const __VLS_42 = __VLS_41({
        label: "涨停",
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "pos" },
    });
    (__VLS_ctx.snap.breadth.limit_up ?? '—');
    var __VLS_43;
    const __VLS_44 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        label: "跌停",
    }));
    const __VLS_46 = __VLS_45({
        label: "跌停",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    __VLS_47.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "neg" },
    });
    (__VLS_ctx.snap.breadth.limit_down ?? '—');
    var __VLS_47;
    const __VLS_48 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        label: "多空比",
    }));
    const __VLS_50 = __VLS_49({
        label: "多空比",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    __VLS_51.slots.default;
    (__VLS_ctx.snap.breadth.advance_decline_ratio?.toFixed(2) ?? '—');
    var __VLS_51;
    var __VLS_27;
    var __VLS_11;
    const __VLS_52 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        shadow: "never",
    }));
    const __VLS_54 = __VLS_53({
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    __VLS_55.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_55.slots;
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "northbound" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "big" },
        ...{ class: ((__VLS_ctx.snap.northbound_net ?? 0) >= 0 ? 'pos' : 'neg') },
    });
    (__VLS_ctx.fmtFlow(__VLS_ctx.snap.northbound_net));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "muted" },
    });
    var __VLS_55;
}
else {
    const __VLS_56 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
        description: "未获取到大盘数据",
    }));
    const __VLS_58 = __VLS_57({
        description: "未获取到大盘数据",
    }, ...__VLS_functionalComponentArgsRest(__VLS_57));
}
/** @type {__VLS_StyleScopedClasses['page']} */ ;
/** @type {__VLS_StyleScopedClasses['indices']} */ ;
/** @type {__VLS_StyleScopedClasses['idx-card']} */ ;
/** @type {__VLS_StyleScopedClasses['idx-name']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['idx-last']} */ ;
/** @type {__VLS_StyleScopedClasses['two-cols']} */ ;
/** @type {__VLS_StyleScopedClasses['breadth']} */ ;
/** @type {__VLS_StyleScopedClasses['breadth-bars']} */ ;
/** @type {__VLS_StyleScopedClasses['bar']} */ ;
/** @type {__VLS_StyleScopedClasses['pos-bg']} */ ;
/** @type {__VLS_StyleScopedClasses['bar']} */ ;
/** @type {__VLS_StyleScopedClasses['neutral-bg']} */ ;
/** @type {__VLS_StyleScopedClasses['bar']} */ ;
/** @type {__VLS_StyleScopedClasses['neg-bg']} */ ;
/** @type {__VLS_StyleScopedClasses['pos']} */ ;
/** @type {__VLS_StyleScopedClasses['neg']} */ ;
/** @type {__VLS_StyleScopedClasses['pos']} */ ;
/** @type {__VLS_StyleScopedClasses['neg']} */ ;
/** @type {__VLS_StyleScopedClasses['northbound']} */ ;
/** @type {__VLS_StyleScopedClasses['big']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            snap: snap,
            loading: loading,
            fmtFlow: fmtFlow,
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