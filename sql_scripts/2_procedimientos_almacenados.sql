-- ==========================================
-- 1. Procedimiento: sp_actualizar_rastreo
-- Descripción: Permite insertar un nuevo estado en el historial de rastreo de un paquete y automáticamente 
-- actualiza el estado principal en la tabla 'paquetes'. Todo dentro de una misma transacción.
-- ==========================================
CREATE OR REPLACE PROCEDURE sp_actualizar_rastreo(
    p_paquete_id INTEGER,
    p_estado VARCHAR,
    p_ubicacion VARCHAR,
    p_comentarios TEXT,
    p_usuario_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Insertar el nuevo movimiento en el historial
    INSERT INTO historial_rastreo (paquete_id, estado, ubicacion, comentarios, creado_en, creado_por)
    VALUES (p_paquete_id, p_estado, p_ubicacion, p_comentarios, CURRENT_TIMESTAMP, p_usuario_id);
    
    -- 2. Actualizar el estado principal del paquete
    UPDATE paquetes 
    SET estado_rastreo = p_estado
    WHERE id = p_paquete_id;
END;
$$;

-- ==========================================
-- 2. Procedimiento: sp_liquidar_factura
-- Descripción: Suma el costo de todos los paquetes asociados a una factura y actualiza el total de la misma.
-- Útil para asegurar que el total no se descuadre si los costos de envío cambian.
-- ==========================================
CREATE OR REPLACE PROCEDURE sp_liquidar_factura(
    p_factura_id INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_nuevo_total FLOAT;
BEGIN
    -- Calcular la suma de costos de los paquetes de esa factura
    SELECT COALESCE(SUM(costo), 0) INTO v_nuevo_total
    FROM paquetes
    WHERE factura_id = p_factura_id;
    
    -- Actualizar la factura con el nuevo total
    UPDATE facturas
    SET total = v_nuevo_total
    WHERE id = p_factura_id;
END;
$$;

-- ==========================================
-- 3. Procedimiento: sp_registrar_pago
-- Descripción: Registra un pago en la factura. Si el total abonado llega a igualar o superar el total 
-- de la factura, la factura pasa automáticamente a estado 'pagada'.
-- ==========================================
CREATE OR REPLACE PROCEDURE sp_registrar_pago(
    p_factura_id INTEGER,
    p_monto FLOAT,
    p_metodo_pago VARCHAR,
    p_referencia VARCHAR,
    p_usuario_id INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_factura FLOAT;
    v_total_pagado FLOAT;
BEGIN
    -- Insertar el registro del pago
    INSERT INTO pagos (factura_id, monto, metodo_pago, referencia, fecha_pago, registrado_por)
    VALUES (p_factura_id, p_monto, p_metodo_pago, p_referencia, CURRENT_TIMESTAMP, p_usuario_id);
    
    -- Obtener el total de la factura y lo que se ha pagado hasta ahora
    SELECT total INTO v_total_factura FROM facturas WHERE id = p_factura_id;
    SELECT COALESCE(SUM(monto), 0) INTO v_total_pagado FROM pagos WHERE factura_id = p_factura_id;
    
    -- Si ya se cubrió el total, cambiar estado
    IF v_total_pagado >= v_total_factura THEN
        UPDATE facturas SET estado = 'pagada' WHERE id = p_factura_id;
    END IF;
END;
$$;
