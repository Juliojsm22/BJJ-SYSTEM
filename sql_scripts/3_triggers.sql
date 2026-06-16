-- ==========================================
-- 1. Trigger: trg_validar_peso_paquete
-- Descripción: Regla de negocio a nivel de base de datos que evita que se pueda registrar o actualizar
-- un paquete con un peso de 0 o negativo, previniendo errores de cálculo en costos.
-- ==========================================
CREATE OR REPLACE FUNCTION fn_validar_peso()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.peso <= 0 THEN
        RAISE EXCEPTION 'Regla de Negocio: El peso del paquete debe ser mayor a 0 libras.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_peso_paquete
BEFORE INSERT OR UPDATE ON paquetes
FOR EACH ROW
EXECUTE FUNCTION fn_validar_peso();

-- ==========================================
-- 2. Trigger: trg_auditar_eliminacion_paquete
-- Descripción: Antes de que un paquete sea borrado de la base de datos, inserta un registro
-- en la tabla de actividades para dejar rastro de que existió y fue eliminado.
-- ==========================================
CREATE OR REPLACE FUNCTION fn_auditar_eliminacion_paquete()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO registro_actividades (usuario_id, accion, detalles, fecha)
    -- Asumimos el usuario 1 (admin) si no hay contexto, o puedes ajustarlo
    VALUES (1, 'Eliminó Paquete', 'Tracking: ' || OLD.tracking_number || ', Nombre: ' || OLD.nombre, CURRENT_TIMESTAMP);
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auditar_eliminacion_paquete
BEFORE DELETE ON paquetes
FOR EACH ROW
EXECUTE FUNCTION fn_auditar_eliminacion_paquete();

-- ==========================================
-- 3. Trigger: trg_impedir_borrado_factura_pagada
-- Descripción: Regla de negocio que bloquea la eliminación de una factura si esta ya tiene estado 'pagada'.
-- Esto evita que se pierda información financiera contable.
-- ==========================================
CREATE OR REPLACE FUNCTION fn_impedir_borrado_factura()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.estado = 'pagada' THEN
        RAISE EXCEPTION 'Seguridad Contable: No se puede eliminar una factura que ya ha sido pagada.';
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_impedir_borrado_factura_pagada
BEFORE DELETE ON facturas
FOR EACH ROW
EXECUTE FUNCTION fn_impedir_borrado_factura();
