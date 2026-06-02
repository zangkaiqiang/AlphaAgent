import { Search } from '@element-plus/icons-vue';
const __VLS_props = defineProps();
const emit = defineEmits();
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onUpdate:modelValue': {} },
    ...{ 'onKeyup': {} },
    modelValue: (__VLS_ctx.modelValue),
    placeholder: "6 位股票代码,如 600000",
    clearable: true,
}));
const __VLS_2 = __VLS_1({
    ...{ 'onUpdate:modelValue': {} },
    ...{ 'onKeyup': {} },
    modelValue: (__VLS_ctx.modelValue),
    placeholder: "6 位股票代码,如 600000",
    clearable: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
let __VLS_6;
const __VLS_7 = {
    'onUpdate:modelValue': (...[$event]) => {
        __VLS_ctx.emit('update:modelValue', $event);
    }
};
const __VLS_8 = {
    onKeyup: (...[$event]) => {
        __VLS_ctx.emit('submit');
    }
};
var __VLS_9 = {};
__VLS_3.slots.default;
{
    const { prefix: __VLS_thisSlot } = __VLS_3.slots;
    const __VLS_10 = {}.ElIcon;
    /** @type {[typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, ]} */ ;
    // @ts-ignore
    const __VLS_11 = __VLS_asFunctionalComponent(__VLS_10, new __VLS_10({}));
    const __VLS_12 = __VLS_11({}, ...__VLS_functionalComponentArgsRest(__VLS_11));
    __VLS_13.slots.default;
    const __VLS_14 = {}.Search;
    /** @type {[typeof __VLS_components.Search, ]} */ ;
    // @ts-ignore
    const __VLS_15 = __VLS_asFunctionalComponent(__VLS_14, new __VLS_14({}));
    const __VLS_16 = __VLS_15({}, ...__VLS_functionalComponentArgsRest(__VLS_15));
    var __VLS_13;
}
{
    const { append: __VLS_thisSlot } = __VLS_3.slots;
    const __VLS_18 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_19 = __VLS_asFunctionalComponent(__VLS_18, new __VLS_18({
        ...{ 'onClick': {} },
        type: "primary",
        icon: (__VLS_ctx.Search),
    }));
    const __VLS_20 = __VLS_19({
        ...{ 'onClick': {} },
        type: "primary",
        icon: (__VLS_ctx.Search),
    }, ...__VLS_functionalComponentArgsRest(__VLS_19));
    let __VLS_22;
    let __VLS_23;
    let __VLS_24;
    const __VLS_25 = {
        onClick: (...[$event]) => {
            __VLS_ctx.emit('submit');
        }
    };
    __VLS_21.slots.default;
    var __VLS_21;
}
var __VLS_3;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Search: Search,
            emit: emit,
        };
    },
    __typeEmits: {},
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeEmits: {},
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=SymbolPicker.vue.js.map