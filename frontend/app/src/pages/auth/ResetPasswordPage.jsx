import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { authAPI } from '../../utils/api'

const ResetPasswordPage = () => {
  const { token } = useParams()
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await authAPI.resetPassword({ token, new_password: newPassword, confirm_password: confirmPassword })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка сброса пароля')
    }
  }

  if (success) return <div>Пароль успешно изменён! Перенаправляем на вход...</div>

  return (
    <form onSubmit={handleSubmit} className="max-w-md mx-auto mt-10">
      <h2 className="text-2xl mb-4">Сброс пароля</h2>
      <input
        type="password"
        className="form-control mb-2"
        placeholder="Новый пароль"
        value={newPassword}
        onChange={e => setNewPassword(e.target.value)}
        required
      />
      <input
        type="password"
        className="form-control mb-2"
        placeholder="Подтвердите пароль"
        value={confirmPassword}
        onChange={e => setConfirmPassword(e.target.value)}
        required
      />
      <button className="btn btn-primary w-full" type="submit">Сменить пароль</button>
      {error && <div className="alert alert-danger mt-2">{error}</div>}
    </form>
  )
}

export default ResetPasswordPage 