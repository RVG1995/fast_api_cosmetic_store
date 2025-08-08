import StatusesManager from '../../components/admin/StatusesManager.jsx';

const AdminOrderStatuses = () => (
  <StatusesManager
    pageTitle="Управление статусами заказов"
    resourcePath="order-statuses"
    emptyListText="Статусы заказов не найдены"
    createModalTitle="Создание статуса заказа"
    editModalTitle="Редактирование статуса заказа"
    createSuccessMsg="Статус заказа успешно создан"
    updateSuccessMsg="Статус заказа успешно обновлен"
    deleteSuccessMsg="Статус заказа успешно удален"
    loadErrorMsg="Не удалось загрузить статусы заказов. Пожалуйста, попробуйте позже."
    saveErrorMsg="Не удалось сохранить статус заказа. Пожалуйста, попробуйте позже."
    deleteErrorMsg="Не удалось удалить статус заказа. Пожалуйста, попробуйте позже."
    initialExtraFields={{ allow_cancel: true, is_final: false }}
    extraFieldDefs={[
      { name: 'allow_cancel', label: 'Разрешить отмену заказа', type: 'checkbox', help: 'Если отмечено, заказ можно отменить' },
      { name: 'is_final', label: 'Финальный статус', type: 'checkbox', help: 'Финальный — заказ выполнен или отменен' },
    ]}
    tableExtraColumns={[
      { header: 'Отмена разрешена', render: (row) => (row.allow_cancel ? 'Да' : 'Нет') },
      { header: 'Финальный статус', render: (row) => (row.is_final ? 'Да' : 'Нет') },
    ]}
  />
);

export default AdminOrderStatuses; 