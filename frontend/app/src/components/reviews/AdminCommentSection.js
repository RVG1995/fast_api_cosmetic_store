import React from 'react';
import { Card } from 'react-bootstrap';
import { formatDate } from '../../utils/dateUtils';

const AdminCommentSection = ({ comments }) => {
  // Если нет комментариев, ничего не отображаем
  if (!comments || comments.length === 0) {
    return null;
  }

  return (
    <Card className="mt-3 border-primary">
      <Card.Header className="bg-primary bg-gradient text-white">
        <h6 className="mb-0">
          <i className="bi bi-chat-dots me-2"></i>
          Ответ администрации:
        </h6>
      </Card.Header>
      <Card.Body className="pb-2">
        {comments.map((comment, index) => (
          <Card key={comment.id || index} className="mb-2">
            <Card.Body className="py-2">
              <div className="mb-1">
                {comment.content}
              </div>
              <div className="text-muted small d-flex justify-content-between">
                <div>
                  <i className="bi bi-person me-1"></i>
                  {comment.admin_name || 'Администратор'}
                </div>
                <div>
                  <i className="bi bi-calendar me-1"></i>
                  {formatDate(comment.created_at)}
                </div>
              </div>
            </Card.Body>
          </Card>
        ))}
      </Card.Body>
    </Card>
  );
};

export default AdminCommentSection; 