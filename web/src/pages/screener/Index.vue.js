import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import dayjs from 'dayjs';
import { screenerApi } from '@/api/screener';
const form = reactive({
    label: '',
    universeSource: 'akshare_index',
    indexCode: '000300',
    symbolsText: '600000\n000001',
    asOf: dayjs().format('YYYY-MM-DD'),
    lookbackDays: 120,
    topN: 30,
});
const catalog = ref(null);
const selectedRules = reactive({});
const ruleWeights = reactive({});
const selectedFilters = reactive({});
onMounted(async () => {
    try {
        catalog.value = await screenerApi.listRules();
        // Pre-select first rule if any and set default weights
        if (catalog.value) {
            for (const r of catalog.value.rules) {
                selectedRules[r.type] = false;
                ruleWeights[r.type] = 1.0;
            }
            for (const f of catalog.value.filters) {
                selectedFilters[f.type] = false;
            }
        }
    }
    catch (e) {
        console.error('Failed to load screener rules', e);
    }
});
const job = ref(null);
const screenResult = ref(null);
let ws = null;
const statusLabel = computed(() => {
    const map = {
        pending: '等待中',
        running: '运行中',
        completed: '完成',
        failed: '失败',
        cancelled: '已取消',
    };
    return map[job.value?.status ?? ''] ?? '';
});
const statusType = computed(() => {
    const map = {
        pending: 'info',
        running: 'warning',
        completed: 'success',
        failed: 'danger',
        cancelled: 'info',
    };
    return map[job.value?.status ?? ''] ?? 'info';
});
const progressStatus = computed(() => {
    if (job.value?.status === 'completed')
        return 'success';
    if (job.value?.status === 'failed')
        return 'exception';
    return undefined;
});
function buildConfig() {
    const universe = form.universeSource === 'akshare_index'
        ? { source: 'akshare_index', index_code: form.indexCode }
        : {
            source: 'static',
            symbols: form.symbolsText
                .split('\n')
                .map((s) => s.trim())
                .filter(Boolean),
        };
    const filters = Object.entries(selectedFilters)
        .filter(([, checked]) => checked)
        .map(([type]) => ({ type }));
    const rules = Object.entries(selectedRules)
        .filter(([, checked]) => checked)
        .map(([type]) => ({ type, weight: ruleWeights[type] ?? 1.0 }));
    return {
        universe,
        data: {
            source: 'akshare',
            adjust: 'qfq',
            cache_dir: './data/cache',
            freq: '1d',
        },
        meta: { source: 'akshare' },
        as_of: form.asOf,
        lookback_days: form.lookbackDays,
        calendar_enabled: true,
        filters,
        rules,
        output: { top_n: form.topN },
    };
}
async function submit() {
    screenResult.value = null;
    closeWs();
    try {
        const { job_id } = await screenerApi.submit({
            config: buildConfig(),
            label: form.label || undefined,
        });
        job.value = await screenerApi.get(job_id);
        ws = screenerApi.watch(job_id, async (info) => {
            job.value = info;
            if (info.status === 'completed') {
                screenResult.value = await screenerApi.result(info.id);
                ElMessage.success('选股完成');
            }
            if (info.status === 'failed')
                ElMessage.error(info.error ?? '选股失败');
        });
    }
    catch (e) {
        console.error(e);
    }
}
async function cancel() {
    if (!job.value)
        return;
    await screenerApi.cancel(job.value.id);
}
function closeWs() {
    ws?.close();
    ws = null;
}
onBeforeUnmount(closeWs);
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "grid" },
});
const __VLS_0 = {}.ElCard;
/** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "card form-card" },
    shadow: "never",
}));
const __VLS_2 = __VLS_1({
    ...{ class: "card form-card" },
    shadow: "never",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
{
    const { header: __VLS_thisSlot } = __VLS_3.slots;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
}
const __VLS_4 = {}.ElForm;
/** @type {[typeof __VLS_components.ElForm, typeof __VLS_components.elForm, typeof __VLS_components.ElForm, typeof __VLS_components.elForm, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    model: (__VLS_ctx.form),
    labelPosition: "top",
    size: "default",
}));
const __VLS_6 = __VLS_5({
    model: (__VLS_ctx.form),
    labelPosition: "top",
    size: "default",
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
__VLS_7.slots.default;
const __VLS_8 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    label: "标签(可选)",
}));
const __VLS_10 = __VLS_9({
    label: "标签(可选)",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_11.slots.default;
const __VLS_12 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    modelValue: (__VLS_ctx.form.label),
    placeholder: "给这次选股起个名字",
}));
const __VLS_14 = __VLS_13({
    modelValue: (__VLS_ctx.form.label),
    placeholder: "给这次选股起个名字",
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
var __VLS_11;
const __VLS_16 = {}.ElDivider;
/** @type {[typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    contentPosition: "left",
}));
const __VLS_18 = __VLS_17({
    contentPosition: "left",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_19.slots.default;
var __VLS_19;
const __VLS_20 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    label: "来源",
}));
const __VLS_22 = __VLS_21({
    label: "来源",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
const __VLS_24 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    modelValue: (__VLS_ctx.form.universeSource),
    ...{ style: {} },
}));
const __VLS_26 = __VLS_25({
    modelValue: (__VLS_ctx.form.universeSource),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_27.slots.default;
const __VLS_28 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    label: "指数成分(AkShare)",
    value: "akshare_index",
}));
const __VLS_30 = __VLS_29({
    label: "指数成分(AkShare)",
    value: "akshare_index",
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
const __VLS_32 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    label: "自定义列表",
    value: "static",
}));
const __VLS_34 = __VLS_33({
    label: "自定义列表",
    value: "static",
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
var __VLS_27;
var __VLS_23;
if (__VLS_ctx.form.universeSource === 'akshare_index') {
    const __VLS_36 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        label: "指数代码",
    }));
    const __VLS_38 = __VLS_37({
        label: "指数代码",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    __VLS_39.slots.default;
    const __VLS_40 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        modelValue: (__VLS_ctx.form.indexCode),
        placeholder: "例如 000300",
    }));
    const __VLS_42 = __VLS_41({
        modelValue: (__VLS_ctx.form.indexCode),
        placeholder: "例如 000300",
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    var __VLS_39;
}
else {
    const __VLS_44 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        label: "股票代码(每行一个)",
    }));
    const __VLS_46 = __VLS_45({
        label: "股票代码(每行一个)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    __VLS_47.slots.default;
    const __VLS_48 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        modelValue: (__VLS_ctx.form.symbolsText),
        type: "textarea",
        rows: (4),
        placeholder: "600000&#10;000001",
    }));
    const __VLS_50 = __VLS_49({
        modelValue: (__VLS_ctx.form.symbolsText),
        type: "textarea",
        rows: (4),
        placeholder: "600000&#10;000001",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    var __VLS_47;
}
const __VLS_52 = {}.ElDivider;
/** @type {[typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, ]} */ ;
// @ts-ignore
const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
    contentPosition: "left",
}));
const __VLS_54 = __VLS_53({
    contentPosition: "left",
}, ...__VLS_functionalComponentArgsRest(__VLS_53));
__VLS_55.slots.default;
var __VLS_55;
const __VLS_56 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
    label: "截止日期",
}));
const __VLS_58 = __VLS_57({
    label: "截止日期",
}, ...__VLS_functionalComponentArgsRest(__VLS_57));
__VLS_59.slots.default;
const __VLS_60 = {}.ElDatePicker;
/** @type {[typeof __VLS_components.ElDatePicker, typeof __VLS_components.elDatePicker, ]} */ ;
// @ts-ignore
const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
    modelValue: (__VLS_ctx.form.asOf),
    type: "date",
    valueFormat: "YYYY-MM-DD",
    placeholder: "选择日期",
    ...{ style: {} },
}));
const __VLS_62 = __VLS_61({
    modelValue: (__VLS_ctx.form.asOf),
    type: "date",
    valueFormat: "YYYY-MM-DD",
    placeholder: "选择日期",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_61));
var __VLS_59;
const __VLS_64 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
    label: "回看天数",
}));
const __VLS_66 = __VLS_65({
    label: "回看天数",
}, ...__VLS_functionalComponentArgsRest(__VLS_65));
__VLS_67.slots.default;
const __VLS_68 = {}.ElInputNumber;
/** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
// @ts-ignore
const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
    modelValue: (__VLS_ctx.form.lookbackDays),
    min: (10),
    max: (500),
    step: (10),
    ...{ style: {} },
}));
const __VLS_70 = __VLS_69({
    modelValue: (__VLS_ctx.form.lookbackDays),
    min: (10),
    max: (500),
    step: (10),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_69));
var __VLS_67;
const __VLS_72 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
    label: "输出 Top N",
}));
const __VLS_74 = __VLS_73({
    label: "输出 Top N",
}, ...__VLS_functionalComponentArgsRest(__VLS_73));
__VLS_75.slots.default;
const __VLS_76 = {}.ElInputNumber;
/** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
    modelValue: (__VLS_ctx.form.topN),
    min: (5),
    max: (200),
    step: (5),
    ...{ style: {} },
}));
const __VLS_78 = __VLS_77({
    modelValue: (__VLS_ctx.form.topN),
    min: (5),
    max: (200),
    step: (5),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_77));
var __VLS_75;
const __VLS_80 = {}.ElDivider;
/** @type {[typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, ]} */ ;
// @ts-ignore
const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
    contentPosition: "left",
}));
const __VLS_82 = __VLS_81({
    contentPosition: "left",
}, ...__VLS_functionalComponentArgsRest(__VLS_81));
__VLS_83.slots.default;
var __VLS_83;
if (__VLS_ctx.catalog) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    for (const [f] of __VLS_getVForSourceType((__VLS_ctx.catalog.filters))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            key: (f.type),
            ...{ class: "rule-row" },
        });
        const __VLS_84 = {}.ElCheckbox;
        /** @type {[typeof __VLS_components.ElCheckbox, typeof __VLS_components.elCheckbox, typeof __VLS_components.ElCheckbox, typeof __VLS_components.elCheckbox, ]} */ ;
        // @ts-ignore
        const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
            modelValue: (__VLS_ctx.selectedFilters[f.type]),
        }));
        const __VLS_86 = __VLS_85({
            modelValue: (__VLS_ctx.selectedFilters[f.type]),
        }, ...__VLS_functionalComponentArgsRest(__VLS_85));
        __VLS_87.slots.default;
        (f.type);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (f.class_name);
        var __VLS_87;
    }
    if (__VLS_ctx.catalog.filters.length === 0) {
        const __VLS_88 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
            description: "暂无过滤器",
            imageSize: (40),
        }));
        const __VLS_90 = __VLS_89({
            description: "暂无过滤器",
            imageSize: (40),
        }, ...__VLS_functionalComponentArgsRest(__VLS_89));
    }
}
else {
    const __VLS_92 = {}.ElSkeleton;
    /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
    // @ts-ignore
    const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
        rows: (2),
        animated: true,
    }));
    const __VLS_94 = __VLS_93({
        rows: (2),
        animated: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_93));
}
const __VLS_96 = {}.ElDivider;
/** @type {[typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, ]} */ ;
// @ts-ignore
const __VLS_97 = __VLS_asFunctionalComponent(__VLS_96, new __VLS_96({
    contentPosition: "left",
}));
const __VLS_98 = __VLS_97({
    contentPosition: "left",
}, ...__VLS_functionalComponentArgsRest(__VLS_97));
__VLS_99.slots.default;
var __VLS_99;
if (__VLS_ctx.catalog) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    for (const [r] of __VLS_getVForSourceType((__VLS_ctx.catalog.rules))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            key: (r.type),
            ...{ class: "rule-row" },
        });
        const __VLS_100 = {}.ElCheckbox;
        /** @type {[typeof __VLS_components.ElCheckbox, typeof __VLS_components.elCheckbox, typeof __VLS_components.ElCheckbox, typeof __VLS_components.elCheckbox, ]} */ ;
        // @ts-ignore
        const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
            modelValue: (__VLS_ctx.selectedRules[r.type]),
            ...{ style: {} },
        }));
        const __VLS_102 = __VLS_101({
            modelValue: (__VLS_ctx.selectedRules[r.type]),
            ...{ style: {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_101));
        __VLS_103.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "rule-label" },
        });
        (r.type);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (r.category);
        var __VLS_103;
        if (__VLS_ctx.selectedRules[r.type]) {
            const __VLS_104 = {}.ElInputNumber;
            /** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
            // @ts-ignore
            const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
                modelValue: (__VLS_ctx.ruleWeights[r.type]),
                min: (0),
                max: (10),
                step: (0.5),
                precision: (1),
                size: "small",
                ...{ style: {} },
            }));
            const __VLS_106 = __VLS_105({
                modelValue: (__VLS_ctx.ruleWeights[r.type]),
                min: (0),
                max: (10),
                step: (0.5),
                precision: (1),
                size: "small",
                ...{ style: {} },
            }, ...__VLS_functionalComponentArgsRest(__VLS_105));
        }
    }
    if (__VLS_ctx.catalog.rules.length === 0) {
        const __VLS_108 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
            description: "暂无规则",
            imageSize: (40),
        }));
        const __VLS_110 = __VLS_109({
            description: "暂无规则",
            imageSize: (40),
        }, ...__VLS_functionalComponentArgsRest(__VLS_109));
    }
}
else {
    const __VLS_112 = {}.ElSkeleton;
    /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
    // @ts-ignore
    const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
        rows: (3),
        animated: true,
    }));
    const __VLS_114 = __VLS_113({
        rows: (3),
        animated: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_113));
}
const __VLS_116 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
    ...{ style: {} },
}));
const __VLS_118 = __VLS_117({
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_117));
__VLS_119.slots.default;
const __VLS_120 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
    ...{ 'onClick': {} },
    type: "primary",
    loading: (__VLS_ctx.job?.status === 'running' || __VLS_ctx.job?.status === 'pending'),
    ...{ style: {} },
}));
const __VLS_122 = __VLS_121({
    ...{ 'onClick': {} },
    type: "primary",
    loading: (__VLS_ctx.job?.status === 'running' || __VLS_ctx.job?.status === 'pending'),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_121));
let __VLS_124;
let __VLS_125;
let __VLS_126;
const __VLS_127 = {
    onClick: (__VLS_ctx.submit)
};
__VLS_123.slots.default;
(__VLS_ctx.job?.status === 'running' || __VLS_ctx.job?.status === 'pending' ? '选股中…' : '运行选股');
var __VLS_123;
if (__VLS_ctx.job?.status === 'running' || __VLS_ctx.job?.status === 'pending') {
    const __VLS_128 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_129 = __VLS_asFunctionalComponent(__VLS_128, new __VLS_128({
        ...{ 'onClick': {} },
        ...{ style: {} },
    }));
    const __VLS_130 = __VLS_129({
        ...{ 'onClick': {} },
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_129));
    let __VLS_132;
    let __VLS_133;
    let __VLS_134;
    const __VLS_135 = {
        onClick: (__VLS_ctx.cancel)
    };
    __VLS_131.slots.default;
    var __VLS_131;
}
var __VLS_119;
var __VLS_7;
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "results" },
});
if (__VLS_ctx.job) {
    const __VLS_136 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
        ...{ class: "card" },
        shadow: "never",
    }));
    const __VLS_138 = __VLS_137({
        ...{ class: "card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_137));
    __VLS_139.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_139.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "job-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.job.id.slice(0, 8));
        const __VLS_140 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
            type: (__VLS_ctx.statusType),
        }));
        const __VLS_142 = __VLS_141({
            type: (__VLS_ctx.statusType),
        }, ...__VLS_functionalComponentArgsRest(__VLS_141));
        __VLS_143.slots.default;
        (__VLS_ctx.statusLabel);
        var __VLS_143;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (__VLS_ctx.job.picks_count !== null ? `${__VLS_ctx.job.picks_count} 只` : '');
    }
    const __VLS_144 = {}.ElProgress;
    /** @type {[typeof __VLS_components.ElProgress, typeof __VLS_components.elProgress, ]} */ ;
    // @ts-ignore
    const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
        percentage: (Math.round((__VLS_ctx.job.progress || 0) * 100)),
        status: (__VLS_ctx.progressStatus),
    }));
    const __VLS_146 = __VLS_145({
        percentage: (Math.round((__VLS_ctx.job.progress || 0) * 100)),
        status: (__VLS_ctx.progressStatus),
    }, ...__VLS_functionalComponentArgsRest(__VLS_145));
    if (__VLS_ctx.job.error) {
        const __VLS_148 = {}.ElAlert;
        /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
        // @ts-ignore
        const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({
            type: "error",
            title: (__VLS_ctx.job.error),
            closable: (false),
            ...{ style: {} },
        }));
        const __VLS_150 = __VLS_149({
            type: "error",
            title: (__VLS_ctx.job.error),
            closable: (false),
            ...{ style: {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_149));
    }
    var __VLS_139;
}
if (__VLS_ctx.screenResult) {
    const __VLS_152 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
        ...{ class: "card" },
        shadow: "never",
    }));
    const __VLS_154 = __VLS_153({
        ...{ class: "card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_153));
    __VLS_155.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_155.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "job-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.screenResult.picks.length);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (__VLS_ctx.screenResult.universe_name);
        (__VLS_ctx.screenResult.universe_size);
        (__VLS_ctx.screenResult.filtered_size);
    }
    const __VLS_156 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_157 = __VLS_asFunctionalComponent(__VLS_156, new __VLS_156({
        data: (__VLS_ctx.screenResult.picks),
        stripe: true,
        ...{ style: {} },
    }));
    const __VLS_158 = __VLS_157({
        data: (__VLS_ctx.screenResult.picks),
        stripe: true,
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_157));
    __VLS_159.slots.default;
    const __VLS_160 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
        type: "index",
        label: "#",
        width: "60",
    }));
    const __VLS_162 = __VLS_161({
        type: "index",
        label: "#",
        width: "60",
    }, ...__VLS_functionalComponentArgsRest(__VLS_161));
    const __VLS_164 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
        prop: "symbol",
        label: "代码",
        width: "100",
    }));
    const __VLS_166 = __VLS_165({
        prop: "symbol",
        label: "代码",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_165));
    const __VLS_168 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
        prop: "name",
        label: "名称",
        width: "140",
    }));
    const __VLS_170 = __VLS_169({
        prop: "name",
        label: "名称",
        width: "140",
    }, ...__VLS_functionalComponentArgsRest(__VLS_169));
    const __VLS_172 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
        label: "综合评分",
        width: "120",
    }));
    const __VLS_174 = __VLS_173({
        label: "综合评分",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_173));
    __VLS_175.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_175.slots;
        const { row } = __VLS_getSlotParam(__VLS_thisSlot);
        (row.final_score.toFixed(4));
    }
    var __VLS_175;
    const __VLS_176 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
        label: "规则得分明细",
        type: "expand",
    }));
    const __VLS_178 = __VLS_177({
        label: "规则得分明细",
        type: "expand",
    }, ...__VLS_functionalComponentArgsRest(__VLS_177));
    __VLS_179.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_179.slots;
        const { row } = __VLS_getSlotParam(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "reasons-panel" },
        });
        const __VLS_180 = {}.ElTable;
        /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
        // @ts-ignore
        const __VLS_181 = __VLS_asFunctionalComponent(__VLS_180, new __VLS_180({
            data: (row.reasons),
            size: "small",
            showHeader: (true),
        }));
        const __VLS_182 = __VLS_181({
            data: (row.reasons),
            size: "small",
            showHeader: (true),
        }, ...__VLS_functionalComponentArgsRest(__VLS_181));
        __VLS_183.slots.default;
        const __VLS_184 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
            prop: "rule_name",
            label: "规则",
            width: "180",
        }));
        const __VLS_186 = __VLS_185({
            prop: "rule_name",
            label: "规则",
            width: "180",
        }, ...__VLS_functionalComponentArgsRest(__VLS_185));
        const __VLS_188 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_189 = __VLS_asFunctionalComponent(__VLS_188, new __VLS_188({
            label: "得分",
            width: "100",
        }));
        const __VLS_190 = __VLS_189({
            label: "得分",
            width: "100",
        }, ...__VLS_functionalComponentArgsRest(__VLS_189));
        __VLS_191.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_191.slots;
            const { row: r } = __VLS_getSlotParam(__VLS_thisSlot);
            (r.score.toFixed(4));
        }
        var __VLS_191;
        const __VLS_192 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
            label: "详情",
        }));
        const __VLS_194 = __VLS_193({
            label: "详情",
        }, ...__VLS_functionalComponentArgsRest(__VLS_193));
        __VLS_195.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_195.slots;
            const { row: r } = __VLS_getSlotParam(__VLS_thisSlot);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "detail-text" },
            });
            (JSON.stringify(r.detail));
        }
        var __VLS_195;
        var __VLS_183;
    }
    var __VLS_179;
    var __VLS_159;
    var __VLS_155;
}
if (!__VLS_ctx.job && !__VLS_ctx.screenResult) {
    const __VLS_196 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_197 = __VLS_asFunctionalComponent(__VLS_196, new __VLS_196({
        description: "左侧填好配置后点击「运行选股」",
    }));
    const __VLS_198 = __VLS_197({
        description: "左侧填好配置后点击「运行选股」",
    }, ...__VLS_functionalComponentArgsRest(__VLS_197));
}
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['form-card']} */ ;
/** @type {__VLS_StyleScopedClasses['rule-row']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['rule-row']} */ ;
/** @type {__VLS_StyleScopedClasses['rule-label']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['results']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['job-header']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['job-header']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['reasons-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-text']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            form: form,
            catalog: catalog,
            selectedRules: selectedRules,
            ruleWeights: ruleWeights,
            selectedFilters: selectedFilters,
            job: job,
            screenResult: screenResult,
            statusLabel: statusLabel,
            statusType: statusType,
            progressStatus: progressStatus,
            submit: submit,
            cancel: cancel,
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