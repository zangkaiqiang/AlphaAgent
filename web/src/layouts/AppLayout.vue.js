import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { routes } from '@/router';
const route = useRoute();
const items = computed(() => {
    const root = routes.find(r => r.path === '/');
    if (!root || !root.children)
        return [];
    return root.children.map(c => ({
        path: '/' + c.path,
        title: c.meta?.title || c.path,
        icon: c.meta?.icon || 'Document',
        section: c.meta?.section || '其他',
        enabled: c.meta?.enabled !== false,
    }));
});
const grouped = computed(() => {
    const out = {};
    for (const it of items.value) {
        ;
        (out[it.section] ||= []).push(it);
    }
    return out;
});
const currentTitle = computed(() => {
    const found = items.value.find(it => it.path === route.path);
    return found?.title || '';
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['el-menu-item']} */ ;
// CSS variable injection 
// CSS variable injection end 
const __VLS_0 = {}.ElContainer;
/** @type {[typeof __VLS_components.ElContainer, typeof __VLS_components.elContainer, typeof __VLS_components.ElContainer, typeof __VLS_components.elContainer, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "app-shell" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "app-shell" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
const __VLS_5 = {}.ElAside;
/** @type {[typeof __VLS_components.ElAside, typeof __VLS_components.elAside, typeof __VLS_components.ElAside, typeof __VLS_components.elAside, ]} */ ;
// @ts-ignore
const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
    width: "220px",
    ...{ class: "sidebar" },
}));
const __VLS_7 = __VLS_6({
    width: "220px",
    ...{ class: "sidebar" },
}, ...__VLS_functionalComponentArgsRest(__VLS_6));
__VLS_8.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand" },
});
const __VLS_9 = {}.ElIcon;
/** @type {[typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, ]} */ ;
// @ts-ignore
const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
    size: (22),
}));
const __VLS_11 = __VLS_10({
    size: (22),
}, ...__VLS_functionalComponentArgsRest(__VLS_10));
__VLS_12.slots.default;
const __VLS_13 = {}.Aim;
/** @type {[typeof __VLS_components.Aim, ]} */ ;
// @ts-ignore
const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({}));
const __VLS_15 = __VLS_14({}, ...__VLS_functionalComponentArgsRest(__VLS_14));
var __VLS_12;
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
const __VLS_17 = {}.ElMenu;
/** @type {[typeof __VLS_components.ElMenu, typeof __VLS_components.elMenu, typeof __VLS_components.ElMenu, typeof __VLS_components.elMenu, ]} */ ;
// @ts-ignore
const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
    defaultActive: (__VLS_ctx.route.path),
    router: true,
    ...{ class: "menu" },
}));
const __VLS_19 = __VLS_18({
    defaultActive: (__VLS_ctx.route.path),
    router: true,
    ...{ class: "menu" },
}, ...__VLS_functionalComponentArgsRest(__VLS_18));
__VLS_20.slots.default;
for (const [group, section] of __VLS_getVForSourceType((__VLS_ctx.grouped))) {
    (section);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "section" },
    });
    (section);
    for (const [item] of __VLS_getVForSourceType((group))) {
        const __VLS_21 = {}.ElMenuItem;
        /** @type {[typeof __VLS_components.ElMenuItem, typeof __VLS_components.elMenuItem, typeof __VLS_components.ElMenuItem, typeof __VLS_components.elMenuItem, ]} */ ;
        // @ts-ignore
        const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
            key: (item.path),
            index: (item.path),
            disabled: (item.enabled === false),
        }));
        const __VLS_23 = __VLS_22({
            key: (item.path),
            index: (item.path),
            disabled: (item.enabled === false),
        }, ...__VLS_functionalComponentArgsRest(__VLS_22));
        __VLS_24.slots.default;
        const __VLS_25 = {}.ElIcon;
        /** @type {[typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, ]} */ ;
        // @ts-ignore
        const __VLS_26 = __VLS_asFunctionalComponent(__VLS_25, new __VLS_25({}));
        const __VLS_27 = __VLS_26({}, ...__VLS_functionalComponentArgsRest(__VLS_26));
        __VLS_28.slots.default;
        const __VLS_29 = ((item.icon));
        // @ts-ignore
        const __VLS_30 = __VLS_asFunctionalComponent(__VLS_29, new __VLS_29({}));
        const __VLS_31 = __VLS_30({}, ...__VLS_functionalComponentArgsRest(__VLS_30));
        var __VLS_28;
        {
            const { title: __VLS_thisSlot } = __VLS_24.slots;
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (item.title);
            if (item.enabled === false) {
                const __VLS_33 = {}.ElTag;
                /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
                // @ts-ignore
                const __VLS_34 = __VLS_asFunctionalComponent(__VLS_33, new __VLS_33({
                    size: "small",
                    type: "info",
                    effect: "plain",
                    round: true,
                }));
                const __VLS_35 = __VLS_34({
                    size: "small",
                    type: "info",
                    effect: "plain",
                    round: true,
                }, ...__VLS_functionalComponentArgsRest(__VLS_34));
                __VLS_36.slots.default;
                var __VLS_36;
            }
        }
        var __VLS_24;
    }
}
var __VLS_20;
var __VLS_8;
const __VLS_37 = {}.ElContainer;
/** @type {[typeof __VLS_components.ElContainer, typeof __VLS_components.elContainer, typeof __VLS_components.ElContainer, typeof __VLS_components.elContainer, ]} */ ;
// @ts-ignore
const __VLS_38 = __VLS_asFunctionalComponent(__VLS_37, new __VLS_37({}));
const __VLS_39 = __VLS_38({}, ...__VLS_functionalComponentArgsRest(__VLS_38));
__VLS_40.slots.default;
const __VLS_41 = {}.ElHeader;
/** @type {[typeof __VLS_components.ElHeader, typeof __VLS_components.elHeader, typeof __VLS_components.ElHeader, typeof __VLS_components.elHeader, ]} */ ;
// @ts-ignore
const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
    ...{ class: "topbar" },
}));
const __VLS_43 = __VLS_42({
    ...{ class: "topbar" },
}, ...__VLS_functionalComponentArgsRest(__VLS_42));
__VLS_44.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "title" },
});
(__VLS_ctx.currentTitle);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "actions" },
});
const __VLS_45 = {}.ElLink;
/** @type {[typeof __VLS_components.ElLink, typeof __VLS_components.elLink, typeof __VLS_components.ElLink, typeof __VLS_components.elLink, ]} */ ;
// @ts-ignore
const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
    underline: (false),
    href: "/api/docs",
    target: "_blank",
}));
const __VLS_47 = __VLS_46({
    underline: (false),
    href: "/api/docs",
    target: "_blank",
}, ...__VLS_functionalComponentArgsRest(__VLS_46));
__VLS_48.slots.default;
var __VLS_48;
var __VLS_44;
const __VLS_49 = {}.ElMain;
/** @type {[typeof __VLS_components.ElMain, typeof __VLS_components.elMain, typeof __VLS_components.ElMain, typeof __VLS_components.elMain, ]} */ ;
// @ts-ignore
const __VLS_50 = __VLS_asFunctionalComponent(__VLS_49, new __VLS_49({
    ...{ class: "content" },
}));
const __VLS_51 = __VLS_50({
    ...{ class: "content" },
}, ...__VLS_functionalComponentArgsRest(__VLS_50));
__VLS_52.slots.default;
const __VLS_53 = {}.RouterView;
/** @type {[typeof __VLS_components.RouterView, typeof __VLS_components.routerView, ]} */ ;
// @ts-ignore
const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({}));
const __VLS_55 = __VLS_54({}, ...__VLS_functionalComponentArgsRest(__VLS_54));
var __VLS_52;
var __VLS_40;
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['app-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['brand']} */ ;
/** @type {__VLS_StyleScopedClasses['menu']} */ ;
/** @type {__VLS_StyleScopedClasses['section']} */ ;
/** @type {__VLS_StyleScopedClasses['topbar']} */ ;
/** @type {__VLS_StyleScopedClasses['title']} */ ;
/** @type {__VLS_StyleScopedClasses['actions']} */ ;
/** @type {__VLS_StyleScopedClasses['content']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            route: route,
            grouped: grouped,
            currentTitle: currentTitle,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
//# sourceMappingURL=AppLayout.vue.js.map