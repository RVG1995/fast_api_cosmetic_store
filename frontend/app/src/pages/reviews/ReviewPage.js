import React from 'react';
import { Container } from 'react-bootstrap';
import ReviewDetail from '../../components/reviews/ReviewDetail';
import { useParams } from 'react-router-dom';

const ReviewPage = () => {
  // Используем useParams для получения id отзыва из URL
  const { id } = useParams();

  return (
    <Container className="py-4">
      <h1 className="mb-4">Просмотр отзыва</h1>
      <ReviewDetail id={id} />
    </Container>
  );
};

export default ReviewPage; 