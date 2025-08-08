import React from 'react';
import PropTypes from 'prop-types';
import { Spinner, Alert } from 'react-bootstrap';
import Pagination from './Pagination';

/**
 * Универсальный лэйаут для страниц со списками: заголовок, контролы, состояние загрузки/ошибок/пусто и пагинация
 */
const ListLayout = ({
  title = null,
  headerExtras = null,
  summary = null,
  loading = false,
  error = null,
  empty = false,
  emptyNode = null,
  children,
  footer = null,
  currentPage = 1,
  totalPages = 1,
  onPageChange = () => {},
  className = '',
}) => {
  return (
    <div className={className}>
      {(title || headerExtras || summary) && (
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div className="d-flex align-items-center gap-3">
            {title && <h2 className="mb-0 fs-4">{title}</h2>}
            {summary && <span className="text-muted">{summary}</span>}
          </div>
          <div>{headerExtras}</div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2 mb-0">Загрузка...</p>
        </div>
      ) : error ? (
        <Alert variant="danger">{error}</Alert>
      ) : empty ? (
        emptyNode || (
          <div className="text-center py-5">
            <i className="bi bi-search fs-1 text-muted"></i>
            <h4 className="mt-3">Ничего не найдено</h4>
          </div>
        )
      ) : (
        <>{children}</>
      )}

      {footer}

      {totalPages > 1 && (
        <div className="d-flex justify-content-center mt-4">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={onPageChange}
          />
        </div>
      )}
    </div>
  );
};

ListLayout.propTypes = {
  title: PropTypes.node,
  headerExtras: PropTypes.node,
  summary: PropTypes.node,
  loading: PropTypes.bool,
  error: PropTypes.node,
  empty: PropTypes.bool,
  emptyNode: PropTypes.node,
  children: PropTypes.node,
  footer: PropTypes.node,
  currentPage: PropTypes.number,
  totalPages: PropTypes.number,
  onPageChange: PropTypes.func,
  className: PropTypes.string,
};

export default ListLayout;


