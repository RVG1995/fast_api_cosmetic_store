import React, { useState } from 'react'
import { authAPI } from '../../utils/api'

const ResetPasswordRequestPage = () => {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await authAPI.requestPasswordReset(email)
      setSent(true)
    } catch (err) {
      if (err.response?.status === 404) {
        setError('Email не зарегистрирован')
      } else {
        setError('Ошибка при отправке запроса')
      }
    }
  }

  if (sent) return (
    <div className="card shadow-sm border-0 mx-auto" style={{ maxWidth: 400 }}>
      <div className="card-body d-flex flex-column align-items-center py-5">
        <i className="bi bi-check-circle-fill text-success mb-3" style={{ fontSize: '2.5rem' }}></i>
        <h5 className="card-title mb-2 text-center">Письмо отправлено</h5>
        <p className="mb-1 text-center">Инструкция по сбросу пароля отправлена на</p>
        <div className="fw-semibold text-primary text-center mb-2" style={{ wordBreak: 'break-all' }}>{email}</div>
        <small className="text-muted text-center">Проверьте папку «Спам», если письмо не пришло в течение 5 минут.</small>
      </div>
    </div>
  )

  return (
    <form onSubmit={handleSubmit} className="max-w-md mx-auto mt-10 p-8 bg-white rounded-xl shadow-lg border border-gray-200">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Восстановление пароля</h2>
      <div className="mb-4">
        <input
          type="email"
          className="form-control block w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition text-gray-900 bg-gray-50"
          placeholder="Ваш email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
      </div>
      <button className="btn btn-primary w-full py-3 text-lg rounded-lg shadow-sm hover:bg-blue-600 transition" type="submit">Отправить ссылку для сброса</button>
      {error && <div className="alert alert-danger mt-4 text-center text-red-600 bg-red-50 border border-red-200 rounded-lg py-2">{error}</div>}
    </form>
  )
}

export default ResetPasswordRequestPage 