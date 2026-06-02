import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import dayjs from 'dayjs';
import { backtestApi } from '@/api/backtest';
import { useStrategiesStore } from '@/stores/strategies';
import EquityChart from '@/components/chart/EquityChart.vue';
import MetricsTable from '@/components/MetricsTable.vue';
import FillsTable from '@/components/FillsTable.vue';
const strategiesStore = useStrategiesStore();
const form = reactive({
    label: '',
    dataSource: 'csv',
    dataRoot: './data',
    symbolsText: '600000\n000001',
    range: [
        dayjs().subtract(1, 'year').format('YYYY-MM-DD'),
        dayjs().format('YYYY-MM-DD'),
    ],
    freq: '1d',
    strategy: 'ma_cross',
    params: {},
    initialCash: 1_000_000,
    targetPct: 0.3,
});
const currentParams = computed(() => {
    const s = strategiesStore.list.find(x => x.name === form.strategy);
    return s?.params || [];
});
function syncDefaultParams() {
    const strat = strategiesStore.list.find(s => s.name === form.strategy);
    if (!strat)
        return;
    const next = {};
    for (const p of strat.params) {
        next[p.name] = form.params[p.name] ?? p.default;
    }
    form.params = next;
}
onMounted(async () => {
    await strategiesStore.load();
    syncDefaultParams();
});
watch(() => strategiesStore.list, () => syncDefaultParams(), { once: true });
const job = ref(null);
const result = ref(null);
let ws = null;
const statusLabel = computed(() => {
    const map = {
        pending: '等待中',
        running: '运行中',
        completed: '完成',
        failed: '失败',
        cancelled: '已取消',
    };
    return map[job.value?.status || ''] || '';
});
const statusType = computed(() => {
    const map = {
        pending: 'info',
        running: 'warning',
        completed: 'success',
        failed: 'danger',
        cancelled: 'info',
    };
    return map[job.value?.status || 'info'];
});
const progressStatus = computed(() => {
    if (job.value?.status === 'completed')
        return 'success';
    if (job.value?.status === 'failed')
        return 'exception';
    return undefined;
});
function buildConfig() {
    const symbols = form.symbolsText
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean);
    const dataCfg = {
        source: form.dataSource,
        symbols,
        start: form.range[0],
        end: form.range[1],
        freq: form.freq,
    };
    if (form.dataSource === 'csv')
        dataCfg.root = form.dataRoot;
    return {
        data: dataCfg,
        strategy: {
            name: form.strategy,
            params: form.params,
        },
        portfolio: {
            initial_cash: form.initialCash,
            target_pct: form.targetPct,
        },
    };
}
async function submit() {
    result.value = null;
    closeWs();
    try {
        const { job_id } = await backtestApi.submit({
            config: buildConfig(),
            label: form.label || undefined,
        });
        job.value = await backtestApi.get(job_id);
        ws = backtestApi.watch(job_id, async (info) => {
            job.value = info;
            if (info.status === 'completed') {
                result.value = await backtestApi.result(info.id);
                ElMessage.success('回测完成');
            }
            if (info.status === 'failed')
                ElMessage.error(info.error || '回测失败');
        });
    }
    catch (e) {
        console.error(e);
    }
}
async function cancel() {
    if (!job.value)
        return;
    await backtestApi.cancel(job.value.id);
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
    placeholder: "给这次回测起个名字",
}));
const __VLS_14 = __VLS_13({
    modelValue: (__VLS_ctx.form.label),
    placeholder: "给这次回测起个名字",
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
    label: "数据源",
}));
const __VLS_22 = __VLS_21({
    label: "数据源",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
const __VLS_24 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    modelValue: (__VLS_ctx.form.dataSource),
    ...{ style: {} },
}));
const __VLS_26 = __VLS_25({
    modelValue: (__VLS_ctx.form.dataSource),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_27.slots.default;
const __VLS_28 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    label: "本地 CSV",
    value: "csv",
}));
const __VLS_30 = __VLS_29({
    label: "本地 CSV",
    value: "csv",
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
const __VLS_32 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    label: "AkShare(免费)",
    value: "akshare",
}));
const __VLS_34 = __VLS_33({
    label: "AkShare(免费)",
    value: "akshare",
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
const __VLS_36 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
    label: "Tushare(需 token)",
    value: "tushare",
}));
const __VLS_38 = __VLS_37({
    label: "Tushare(需 token)",
    value: "tushare",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
var __VLS_27;
var __VLS_23;
if (__VLS_ctx.form.dataSource === 'csv') {
    const __VLS_40 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        label: "CSV 目录",
    }));
    const __VLS_42 = __VLS_41({
        label: "CSV 目录",
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    const __VLS_44 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        modelValue: (__VLS_ctx.form.dataRoot),
        placeholder: "例如 ./data",
    }));
    const __VLS_46 = __VLS_45({
        modelValue: (__VLS_ctx.form.dataRoot),
        placeholder: "例如 ./data",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    var __VLS_43;
}
const __VLS_48 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
    label: "股票代码(每行一个)",
}));
const __VLS_50 = __VLS_49({
    label: "股票代码(每行一个)",
}, ...__VLS_functionalComponentArgsRest(__VLS_49));
__VLS_51.slots.default;
const __VLS_52 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
    modelValue: (__VLS_ctx.form.symbolsText),
    type: "textarea",
    rows: (4),
    placeholder: "600000&#10;000001",
}));
const __VLS_54 = __VLS_53({
    modelValue: (__VLS_ctx.form.symbolsText),
    type: "textarea",
    rows: (4),
    placeholder: "600000&#10;000001",
}, ...__VLS_functionalComponentArgsRest(__VLS_53));
var __VLS_51;
const __VLS_56 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
    label: "时间区间",
}));
const __VLS_58 = __VLS_57({
    label: "时间区间",
}, ...__VLS_functionalComponentArgsRest(__VLS_57));
__VLS_59.slots.default;
const __VLS_60 = {}.ElDatePicker;
/** @type {[typeof __VLS_components.ElDatePicker, typeof __VLS_components.elDatePicker, ]} */ ;
// @ts-ignore
const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
    modelValue: (__VLS_ctx.form.range),
    type: "daterange",
    valueFormat: "YYYY-MM-DD",
    startPlaceholder: "开始",
    endPlaceholder: "结束",
    ...{ style: {} },
}));
const __VLS_62 = __VLS_61({
    modelValue: (__VLS_ctx.form.range),
    type: "daterange",
    valueFormat: "YYYY-MM-DD",
    startPlaceholder: "开始",
    endPlaceholder: "结束",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_61));
var __VLS_59;
const __VLS_64 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
    label: "K 线周期",
}));
const __VLS_66 = __VLS_65({
    label: "K 线周期",
}, ...__VLS_functionalComponentArgsRest(__VLS_65));
__VLS_67.slots.default;
const __VLS_68 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
    modelValue: (__VLS_ctx.form.freq),
    ...{ style: {} },
}));
const __VLS_70 = __VLS_69({
    modelValue: (__VLS_ctx.form.freq),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_69));
__VLS_71.slots.default;
const __VLS_72 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
    label: "日线",
    value: "1d",
}));
const __VLS_74 = __VLS_73({
    label: "日线",
    value: "1d",
}, ...__VLS_functionalComponentArgsRest(__VLS_73));
const __VLS_76 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
    label: "60 分钟",
    value: "60m",
}));
const __VLS_78 = __VLS_77({
    label: "60 分钟",
    value: "60m",
}, ...__VLS_functionalComponentArgsRest(__VLS_77));
const __VLS_80 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
    label: "30 分钟",
    value: "30m",
}));
const __VLS_82 = __VLS_81({
    label: "30 分钟",
    value: "30m",
}, ...__VLS_functionalComponentArgsRest(__VLS_81));
const __VLS_84 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
    label: "15 分钟",
    value: "15m",
}));
const __VLS_86 = __VLS_85({
    label: "15 分钟",
    value: "15m",
}, ...__VLS_functionalComponentArgsRest(__VLS_85));
const __VLS_88 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
    label: "5 分钟",
    value: "5m",
}));
const __VLS_90 = __VLS_89({
    label: "5 分钟",
    value: "5m",
}, ...__VLS_functionalComponentArgsRest(__VLS_89));
const __VLS_92 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
    label: "1 分钟",
    value: "1m",
}));
const __VLS_94 = __VLS_93({
    label: "1 分钟",
    value: "1m",
}, ...__VLS_functionalComponentArgsRest(__VLS_93));
var __VLS_71;
var __VLS_67;
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
const __VLS_100 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
    label: "策略",
}));
const __VLS_102 = __VLS_101({
    label: "策略",
}, ...__VLS_functionalComponentArgsRest(__VLS_101));
__VLS_103.slots.default;
const __VLS_104 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.form.strategy),
    ...{ style: {} },
}));
const __VLS_106 = __VLS_105({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.form.strategy),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_105));
let __VLS_108;
let __VLS_109;
let __VLS_110;
const __VLS_111 = {
    onChange: (__VLS_ctx.syncDefaultParams)
};
__VLS_107.slots.default;
for (const [s] of __VLS_getVForSourceType((__VLS_ctx.strategiesStore.list))) {
    const __VLS_112 = {}.ElOption;
    /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
    // @ts-ignore
    const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
        key: (s.name),
        label: (`${s.name}  —  ${s.class_name}`),
        value: (s.name),
    }));
    const __VLS_114 = __VLS_113({
        key: (s.name),
        label: (`${s.name}  —  ${s.class_name}`),
        value: (s.name),
    }, ...__VLS_functionalComponentArgsRest(__VLS_113));
}
var __VLS_107;
var __VLS_103;
for (const [p] of __VLS_getVForSourceType((__VLS_ctx.currentParams))) {
    const __VLS_116 = {}.ElFormItem;
    /** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
    // @ts-ignore
    const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
        key: (p.name),
        label: (`${p.name} (${p.type})`),
    }));
    const __VLS_118 = __VLS_117({
        key: (p.name),
        label: (`${p.name} (${p.type})`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_117));
    __VLS_119.slots.default;
    if (p.type === 'int' || p.type === 'float') {
        const __VLS_120 = {}.ElInputNumber;
        /** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
        // @ts-ignore
        const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
            modelValue: (__VLS_ctx.form.params[p.name]),
            step: (p.type === 'float' ? 0.1 : 1),
            precision: (p.type === 'float' ? 2 : 0),
            ...{ style: {} },
        }));
        const __VLS_122 = __VLS_121({
            modelValue: (__VLS_ctx.form.params[p.name]),
            step: (p.type === 'float' ? 0.1 : 1),
            precision: (p.type === 'float' ? 2 : 0),
            ...{ style: {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_121));
    }
    else {
        const __VLS_124 = {}.ElInput;
        /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
        // @ts-ignore
        const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
            modelValue: (__VLS_ctx.form.params[p.name]),
        }));
        const __VLS_126 = __VLS_125({
            modelValue: (__VLS_ctx.form.params[p.name]),
        }, ...__VLS_functionalComponentArgsRest(__VLS_125));
    }
    var __VLS_119;
}
const __VLS_128 = {}.ElDivider;
/** @type {[typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, typeof __VLS_components.ElDivider, typeof __VLS_components.elDivider, ]} */ ;
// @ts-ignore
const __VLS_129 = __VLS_asFunctionalComponent(__VLS_128, new __VLS_128({
    contentPosition: "left",
}));
const __VLS_130 = __VLS_129({
    contentPosition: "left",
}, ...__VLS_functionalComponentArgsRest(__VLS_129));
__VLS_131.slots.default;
var __VLS_131;
const __VLS_132 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_133 = __VLS_asFunctionalComponent(__VLS_132, new __VLS_132({
    label: "初始资金",
}));
const __VLS_134 = __VLS_133({
    label: "初始资金",
}, ...__VLS_functionalComponentArgsRest(__VLS_133));
__VLS_135.slots.default;
const __VLS_136 = {}.ElInputNumber;
/** @type {[typeof __VLS_components.ElInputNumber, typeof __VLS_components.elInputNumber, ]} */ ;
// @ts-ignore
const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
    modelValue: (__VLS_ctx.form.initialCash),
    min: (10000),
    step: (100000),
    ...{ style: {} },
}));
const __VLS_138 = __VLS_137({
    modelValue: (__VLS_ctx.form.initialCash),
    min: (10000),
    step: (100000),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_137));
var __VLS_135;
const __VLS_140 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
    label: "单次仓位比例 (target_pct)",
}));
const __VLS_142 = __VLS_141({
    label: "单次仓位比例 (target_pct)",
}, ...__VLS_functionalComponentArgsRest(__VLS_141));
__VLS_143.slots.default;
const __VLS_144 = {}.ElSlider;
/** @type {[typeof __VLS_components.ElSlider, typeof __VLS_components.elSlider, ]} */ ;
// @ts-ignore
const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
    modelValue: (__VLS_ctx.form.targetPct),
    min: (0.05),
    max: (1),
    step: (0.05),
}));
const __VLS_146 = __VLS_145({
    modelValue: (__VLS_ctx.form.targetPct),
    min: (0.05),
    max: (1),
    step: (0.05),
}, ...__VLS_functionalComponentArgsRest(__VLS_145));
var __VLS_143;
const __VLS_148 = {}.ElFormItem;
/** @type {[typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, typeof __VLS_components.ElFormItem, typeof __VLS_components.elFormItem, ]} */ ;
// @ts-ignore
const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({}));
const __VLS_150 = __VLS_149({}, ...__VLS_functionalComponentArgsRest(__VLS_149));
__VLS_151.slots.default;
const __VLS_152 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
    ...{ 'onClick': {} },
    type: "primary",
    loading: (__VLS_ctx.job?.status === 'running'),
    ...{ style: {} },
}));
const __VLS_154 = __VLS_153({
    ...{ 'onClick': {} },
    type: "primary",
    loading: (__VLS_ctx.job?.status === 'running'),
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_153));
let __VLS_156;
let __VLS_157;
let __VLS_158;
const __VLS_159 = {
    onClick: (__VLS_ctx.submit)
};
__VLS_155.slots.default;
(__VLS_ctx.job?.status === 'running' ? '回测中…' : '运行回测');
var __VLS_155;
if (__VLS_ctx.job?.status === 'running') {
    const __VLS_160 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
        ...{ 'onClick': {} },
        ...{ style: {} },
    }));
    const __VLS_162 = __VLS_161({
        ...{ 'onClick': {} },
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_161));
    let __VLS_164;
    let __VLS_165;
    let __VLS_166;
    const __VLS_167 = {
        onClick: (__VLS_ctx.cancel)
    };
    __VLS_163.slots.default;
    var __VLS_163;
}
var __VLS_151;
var __VLS_7;
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "results" },
});
if (__VLS_ctx.job) {
    const __VLS_168 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
        ...{ class: "card" },
        shadow: "never",
    }));
    const __VLS_170 = __VLS_169({
        ...{ class: "card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_169));
    __VLS_171.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_171.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "job-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.job.id.slice(0, 8));
        const __VLS_172 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
            type: (__VLS_ctx.statusType),
        }));
        const __VLS_174 = __VLS_173({
            type: (__VLS_ctx.statusType),
        }, ...__VLS_functionalComponentArgsRest(__VLS_173));
        __VLS_175.slots.default;
        (__VLS_ctx.statusLabel);
        var __VLS_175;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (__VLS_ctx.job.bars_processed);
        (__VLS_ctx.job.bars_total);
        (__VLS_ctx.job.fill_count);
    }
    const __VLS_176 = {}.ElProgress;
    /** @type {[typeof __VLS_components.ElProgress, typeof __VLS_components.elProgress, ]} */ ;
    // @ts-ignore
    const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
        percentage: (Math.round((__VLS_ctx.job.progress || 0) * 100)),
        status: (__VLS_ctx.progressStatus),
    }));
    const __VLS_178 = __VLS_177({
        percentage: (Math.round((__VLS_ctx.job.progress || 0) * 100)),
        status: (__VLS_ctx.progressStatus),
    }, ...__VLS_functionalComponentArgsRest(__VLS_177));
    if (__VLS_ctx.job.error) {
        const __VLS_180 = {}.ElAlert;
        /** @type {[typeof __VLS_components.ElAlert, typeof __VLS_components.elAlert, ]} */ ;
        // @ts-ignore
        const __VLS_181 = __VLS_asFunctionalComponent(__VLS_180, new __VLS_180({
            type: "error",
            title: (__VLS_ctx.job.error),
            closable: (false),
            ...{ style: {} },
        }));
        const __VLS_182 = __VLS_181({
            type: "error",
            title: (__VLS_ctx.job.error),
            closable: (false),
            ...{ style: {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_181));
    }
    var __VLS_171;
}
if (__VLS_ctx.result) {
    const __VLS_184 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
        ...{ class: "card" },
        shadow: "never",
    }));
    const __VLS_186 = __VLS_185({
        ...{ class: "card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_185));
    __VLS_187.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_187.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    }
    /** @type {[typeof EquityChart, ]} */ ;
    // @ts-ignore
    const __VLS_188 = __VLS_asFunctionalComponent(EquityChart, new EquityChart({
        curve: (__VLS_ctx.result.equity_curve),
        byStrategy: (__VLS_ctx.result.equity_by_strategy),
    }));
    const __VLS_189 = __VLS_188({
        curve: (__VLS_ctx.result.equity_curve),
        byStrategy: (__VLS_ctx.result.equity_by_strategy),
    }, ...__VLS_functionalComponentArgsRest(__VLS_188));
    var __VLS_187;
}
if (__VLS_ctx.result) {
    const __VLS_191 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_192 = __VLS_asFunctionalComponent(__VLS_191, new __VLS_191({
        ...{ class: "card" },
        shadow: "never",
    }));
    const __VLS_193 = __VLS_192({
        ...{ class: "card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_192));
    __VLS_194.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_194.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    }
    /** @type {[typeof MetricsTable, ]} */ ;
    // @ts-ignore
    const __VLS_195 = __VLS_asFunctionalComponent(MetricsTable, new MetricsTable({
        perf: (__VLS_ctx.result.performance),
    }));
    const __VLS_196 = __VLS_195({
        perf: (__VLS_ctx.result.performance),
    }, ...__VLS_functionalComponentArgsRest(__VLS_195));
    var __VLS_194;
}
if (__VLS_ctx.result && __VLS_ctx.result.fills.length) {
    const __VLS_198 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_199 = __VLS_asFunctionalComponent(__VLS_198, new __VLS_198({
        ...{ class: "card" },
        shadow: "never",
    }));
    const __VLS_200 = __VLS_199({
        ...{ class: "card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_199));
    __VLS_201.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_201.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.result.fills.length);
    }
    /** @type {[typeof FillsTable, ]} */ ;
    // @ts-ignore
    const __VLS_202 = __VLS_asFunctionalComponent(FillsTable, new FillsTable({
        fills: (__VLS_ctx.result.fills),
    }));
    const __VLS_203 = __VLS_202({
        fills: (__VLS_ctx.result.fills),
    }, ...__VLS_functionalComponentArgsRest(__VLS_202));
    var __VLS_201;
}
if (!__VLS_ctx.job && !__VLS_ctx.result) {
    const __VLS_205 = {}.ElEmpty;
    /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
    // @ts-ignore
    const __VLS_206 = __VLS_asFunctionalComponent(__VLS_205, new __VLS_205({
        description: "左侧填好配置后点击「运行回测」",
    }));
    const __VLS_207 = __VLS_206({
        description: "左侧填好配置后点击「运行回测」",
    }, ...__VLS_functionalComponentArgsRest(__VLS_206));
}
/** @type {__VLS_StyleScopedClasses['grid']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['form-card']} */ ;
/** @type {__VLS_StyleScopedClasses['results']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['job-header']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
/** @type {__VLS_StyleScopedClasses['card']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            EquityChart: EquityChart,
            MetricsTable: MetricsTable,
            FillsTable: FillsTable,
            strategiesStore: strategiesStore,
            form: form,
            currentParams: currentParams,
            syncDefaultParams: syncDefaultParams,
            job: job,
            result: result,
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