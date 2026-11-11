(function (wp) {
    'use strict';
    var el = wp.element.createElement;
    var Fragment = wp.element.Fragment;
    var InnerBlocks = wp.blockEditor.InnerBlocks;
    var InspectorControls = wp.blockEditor.InspectorControls;
    var useBlockProps = wp.blockEditor.useBlockProps;

    function paragraph(className, placeholder, content) {
        var attributes = {className: className, placeholder: placeholder};
        if (content) attributes.content = content;
        return ['core/paragraph', attributes];
    }

    function card(kind) {
        var body = [
            paragraph('text-h3', kind === 'cases' ? 'Название проекта' : 'Название организации'),
            paragraph('case-name', 'Город или направление деятельности'),
            paragraph('', 'Описание: укажите собственные сведения')
        ];
        if (kind === 'cases') body.push(paragraph('', 'Состав оборудования и особенности проекта'));
        return ['core/column', {className: kind === 'cases' ? 'case-card' : 'partner-object'}, [
            ['core/image', {className: 'molberty-block-image', sizeSlug: 'large', linkDestination: 'none'}],
            ['core/group', {className: 'case-card-body', layout: {type: 'default'}}, body]
        ]];
    }

    function template(kind) {
        var cases = kind === 'cases';
        var heading = ['core/group', {className: 'section-heading', layout: {type: 'default'}}, [
            paragraph('eyebrow', '', cases ? 'Кейсы' : 'Творчество объединяет'),
            paragraph('text-h2', 'Заголовок блока', cases ? 'Каким может стать ваше пространство.' : 'От первой линии - до собственной выставки.'),
            paragraph('', 'Вступление к блоку')
        ]];
        return [['core/group', {className: 'wrap section', layout: {type: 'default'}}, [
            heading,
            ['core/columns', {className: 'molberty-cards ' + (cases ? 'case-grid' : 'partner-object-grid')}, [card(kind), card(kind), card(kind)]]
        ]]];
    }

    [
        {kind: 'cases', title: 'Мольберты.ру - Кейсы', icon: 'portfolio'},
        {kind: 'partners', title: 'Мольберты.ру - Творчество объединяет', icon: 'groups'}
    ].forEach(function (definition) {
        wp.blocks.registerBlockType('molberty/' + definition.kind, {
            apiVersion: 3,
            title: definition.title,
            category: 'design',
            icon: definition.icon,
            attributes: {enabled: {type: 'boolean', default: false}},
            supports: {html: false},
            edit: function (props) {
                var visible = props.attributes.enabled === true;
                var wrapper = useBlockProps({className: 'molberty-home-block ' + (definition.kind === 'cases' ? 'cases-section' : 'partner-showcase')});
                return el(Fragment, null,
                    el(InspectorControls, null,
                        el(wp.components.PanelBody, {title: 'Видимость блока', initialOpen: true},
                            el(wp.components.ToggleControl, {
                                label: 'Показывать на сайте',
                                checked: visible,
                                help: 'Скрытие сохраняет все тексты, изображения и карточки для последующего редактирования.',
                                onChange: function (value) { props.setAttributes({enabled: value}); }
                            })
                        )
                    ),
                    el('div', wrapper,
                        el(wp.components.Notice, {status: visible ? 'success' : 'info', isDismissible: false},
                            visible ? 'Блок включён. Изменения появятся на сайте после сохранения страницы.' : 'Блок скрыт на сайте. Наполните его и включите в настройках блока.'
                        ),
                        el(InnerBlocks, {template: template(definition.kind), templateLock: false})
                    )
                );
            },
            save: function () {
                // Retain the native editable blocks even while the server returns no public markup.
                return el(InnerBlocks.Content);
            }
        });
    });
})(window.wp);
