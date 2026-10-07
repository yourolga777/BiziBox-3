from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.product import ProductResponse
from ..schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from ..services.supplier_service import SupplierService

router = APIRouter()


@router.get("/", response_model=List[SupplierResponse])
async def get_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[SupplierResponse]:
    service = SupplierService(session, owner_id=int(current_user.id))
    return await service.get_all(skip=skip, limit=limit)


@router.post("/", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SupplierResponse:
    service = SupplierService(session, owner_id=int(current_user.id))
    supplier = await service.create(data)
    if not supplier:
        raise HTTPException(
            status_code=409,
            detail="Supplier already exists for this contact, or contact not found",
        )
    return supplier


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SupplierResponse:
    service = SupplierService(session, owner_id=int(current_user.id))
    supplier = await service.get_by_id(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SupplierResponse:
    service = SupplierService(session, owner_id=int(current_user.id))
    supplier = await service.update(supplier_id, data)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = SupplierService(session, owner_id=int(current_user.id))
    deleted = await service.delete(supplier_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Supplier not found")


@router.get("/{supplier_id}/products", response_model=List[ProductResponse])
async def get_supplier_products(
    supplier_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ProductResponse]:
    service = SupplierService(session, owner_id=int(current_user.id))
    supplier = await service.get_by_id(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return await service.get_products(supplier_id, skip=skip, limit=limit)
