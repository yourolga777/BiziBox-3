from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.product import (
    ProductCreate,
    ProductImportResult,
    ProductResponse,
    ProductSuggestItem,
    ProductUpdate,
)
from ..services.product_service import ProductService

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    search: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ProductResponse]:
    service = ProductService(session, owner_id=int(current_user.id))
    return await service.get_all(
        search=search,
        supplier_id=supplier_id,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )


@router.get("/archive", response_model=List[ProductResponse])
async def get_archived_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ProductResponse]:
    service = ProductService(session, owner_id=int(current_user.id))
    return await service.get_deleted(skip=skip, limit=limit)


@router.get("/export/csv")
async def export_products_csv(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> Response:
    service = ProductService(session, owner_id=int(current_user.id))
    csv_content = await service.export_csv()
    content = "\uFEFF" + csv_content
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.post("/import", response_model=ProductImportResult)
async def import_products(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProductImportResult:
    service = ProductService(session, owner_id=int(current_user.id))
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8-sig")
    return await service.import_csv(content)


@router.get("/suggest", response_model=List[ProductSuggestItem])
async def suggest_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ProductSuggestItem]:
    service = ProductService(session, owner_id=int(current_user.id))
    return await service.suggest(q, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProductResponse:
    service = ProductService(session, owner_id=int(current_user.id))
    product = await service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProductResponse:
    service = ProductService(session, owner_id=int(current_user.id))
    product = await service.create(data)
    if not product:
        raise HTTPException(status_code=409, detail="Product with this SKU already exists")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProductResponse:
    service = ProductService(session, owner_id=int(current_user.id))
    product = await service.update(product_id, data)
    if not product:
        raise HTTPException(status_code=409, detail="Product with this SKU already exists")
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = ProductService(session, owner_id=int(current_user.id))
    deleted = await service.delete(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")


@router.delete("/{product_id}/permanent", status_code=204)
async def permanent_delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = ProductService(session, owner_id=int(current_user.id))
    deleted = await service.permanent_delete(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")


@router.post("/{product_id}/restore", response_model=ProductResponse)
async def restore_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProductResponse:
    service = ProductService(session, owner_id=int(current_user.id))
    product = await service.restore(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
