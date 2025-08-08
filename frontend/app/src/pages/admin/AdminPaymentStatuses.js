import StatusesManager from '../../components/admin/StatusesManager.jsx';

const AdminPaymentStatuses = () => (
  <StatusesManager
    pageTitle="Управление статусами оплаты"
    resourcePath="payment-statuses"
    emptyListText="Статусы оплаты не найдены"
    createModalTitle="Создание статуса оплаты"
    editModalTitle="Редактирование статуса оплаты"
    createSuccessMsg="Статус оплаты успешно создан"
    updateSuccessMsg="Статус оплаты успешно обновлен"
    deleteSuccessMsg="Статус оплаты успешно удален"
    loadErrorMsg="Не удалось загрузить статусы оплаты. Пожалуйста, попробуйте позже."
    saveErrorMsg="Не удалось сохранить статус оплаты. Пожалуйста, попробуйте позже."
    deleteErrorMsg="Не удалось удалить статус оплаты. Пожалуйста, попробуйте позже."
    initialExtraFields={{ is_paid: false }}
    extraFieldDefs={[
      { name: 'is_paid', label: 'Считается оплаченным', type: 'checkbox', help: 'Заказы с этим статусом считаются оплаченными' },
    ]}
    tableExtraColumns={[
      { header: 'Статус оплаты', render: (row) => (row.is_paid ? 'Оплачено' : 'Не оплачено') },
    ]}
  />
);

export default AdminPaymentStatuses;