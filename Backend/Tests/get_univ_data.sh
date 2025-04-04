#!/bin/bash

echo "TEST Получить данные о вузе с филиалами- OK"
curl -X GET http://localhost:8000/opendata/universities/dd6713c5-8d07-f8f4-e685-bbbe6d0900c8
echo

echo "TEST Получить данные о филиале - OK"
curl -X GET http://localhost:8000/opendata/universities/a97b9f25-dfd5-61ee-628f-806d7fb84aa9
echo

echo "TEST Получить данные о вузе по несуществующему id - BAD"
curl -X GET http://localhost:8000/opendata/universities/ec529ea5
echo
