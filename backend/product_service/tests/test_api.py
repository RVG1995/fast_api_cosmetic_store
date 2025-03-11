import pytest
from httpx import AsyncClient, ASGITransport
from product_service.main import app
import asyncio


#@pytest.fixture(scope="function")
#def event_loop():
 #   loop = asyncio.new_event_loop()
  #  yield loop
   # loop.close()


@pytest.mark.asyncio
async def test_get_products():
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as ac:
        response = await ac.get('/products')
        assert response.status_code == 200

        data = response.json()
       # print(len(data))
        assert data != []
        assert len(data) == 1
        

@pytest.mark.asyncio
async def test_post_products():
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as ac:
        response = await ac.post('/products',data={
            'name': 'test_product',
            'category_id': 1,
            'country_id': 1,
            'brand_id': 1,
            'subcategory_id': 1,
            'price':10,
            'description': 'TEST',
            'stock': 10,
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data == {"ok": "New product was added"}
       # print(len(data))
        #assert data != []
       # assert len(data) == 1
        