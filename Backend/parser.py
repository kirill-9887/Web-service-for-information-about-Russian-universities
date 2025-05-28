import asyncio
import xml.etree.ElementTree as et
from sqlalchemy import select
import config
import db_tables as dbt
import data_models as dm
import datetime
from database import asyncDBSession


async def update_DB(data_filename=config.DATAFILENAME):
    print("BD UPDATING")
    actual_univs_id, actual_eduprogs_id = await xml_parse(filename=data_filename)
    async with asyncDBSession() as db_session:
        cur_univs_result = await db_session.execute(select(dbt.University))
        cur_univs = cur_univs_result.scalars()
        cur_eduprogs_result = await db_session.execute(select(dbt.EduProg))
        cur_eduprogs = cur_eduprogs_result.scalars()
    cur_univs_id = set(univ.id for univ in cur_univs)
    cur_eduprogs_id = set(prog.id for prog in cur_eduprogs)
    univs_to_delete_id = cur_univs_id - actual_univs_id
    eduprogs_to_delete_id = cur_eduprogs_id - actual_eduprogs_id
    print(f"Вузов к удалению: {len(univs_to_delete_id)}. ОП к удалению: {len(eduprogs_to_delete_id)}.")
    for univ_id in univs_to_delete_id:
        await dbt.University.delete(id=univ_id, from_parser=True)
    for eduprog_id in eduprogs_to_delete_id:
        await dbt.EduProg.delete(id=eduprog_id, from_parser=True)


def is_accredited_validator(value) -> int:
    value = dm.to_int_validator(value)
    return int(not value)


async def xml_parse(filename: str):
    def sync_xml_parse():
        univ_models = []
        eduprog_models = []
        today = str(datetime.date.today())
        suppl_statuses = set()
        cert_statuses = set()
        tree = et.parse(filename)
        root = tree.getroot()
        certificates = root.findall("Certificates/Certificate")
        for cert in certificates:
            cert_status_name = cert.find("StatusName").text
            cert_end_date = cert.find("EndDate").text
            cert_statuses.add(cert_status_name)
            if cert_status_name != "Действующее" or cert_end_date and cert_end_date < today:
                continue
            eduorg = cert.find("ActualEducationOrganization")
            univ_model = dm.University(
                id=eduorg.find("Id").text,
                full_name=eduorg.find("FullName").text,
                short_name=eduorg.find("ShortName").text,
                head_edu_org_id=eduorg.find("HeadEduOrgId").text,
                is_branch=eduorg.find("IsBranch").text,
                post_address=eduorg.find("PostAddress").text,
                phone=eduorg.find("Phone").text,
                fax=eduorg.find("Fax").text,
                email=eduorg.find("Email").text,
                web_site=eduorg.find("WebSite").text,
                ogrn=eduorg.find("OGRN").text,
                inn=eduorg.find("INN").text,
                kpp=eduorg.find("KPP").text,
                head_post=eduorg.find("HeadPost").text,
                head_name=eduorg.find("HeadName").text,
                form_name=eduorg.find("FormName").text,
                kind_name=eduorg.find("KindName").text,
                type_name=eduorg.find("TypeName").text,
                region_name=eduorg.find("RegionName").text,
                federal_district_name=eduorg.find("FederalDistrictName").text,
            )
            if ("общеобр" in univ_model.full_name.lower()
                    or "колледж" in univ_model.full_name.lower()
                    or not ("высшего" in univ_model.full_name.lower() or "высшего" in univ_model.type_name.lower())):
                pass
            else:
                univ_models.append(univ_model)
            supplements = cert.findall("Supplements/Supplement")
            for suppl in supplements:
                suppl_status_name = suppl.find("StatusName").text
                suppl_statuses.add(suppl_status_name)
                if suppl_status_name != "Действующее":
                    continue
                suppl_edu_org = suppl.find("ActualEducationOrganization")
                suppl_univ_model = dm.University(
                    id=suppl_edu_org.find("Id").text,
                    full_name=suppl_edu_org.find("FullName").text,
                    short_name=suppl_edu_org.find("ShortName").text,
                    head_edu_org_id=suppl_edu_org.find("HeadEduOrgId").text,
                    is_branch=suppl_edu_org.find("IsBranch").text,
                    post_address=suppl_edu_org.find("PostAddress").text,
                    phone=suppl_edu_org.find("Phone").text,
                    fax=suppl_edu_org.find("Fax").text,
                    email=suppl_edu_org.find("Email").text,
                    web_site=suppl_edu_org.find("WebSite").text,
                    ogrn=suppl_edu_org.find("OGRN").text,
                    inn=suppl_edu_org.find("INN").text,
                    kpp=suppl_edu_org.find("KPP").text,
                    head_post=suppl_edu_org.find("HeadPost").text,
                    head_name=suppl_edu_org.find("HeadName").text,
                    form_name=suppl_edu_org.find("FormName").text,
                    kind_name=suppl_edu_org.find("KindName").text,
                    type_name=suppl_edu_org.find("TypeName").text,
                    region_name=suppl_edu_org.find("RegionName").text,
                    federal_district_name=suppl_edu_org.find("FederalDistrictName").text,
                )
                if ("общеобр" in univ_model.full_name.lower()
                        or "колледж" in univ_model.full_name.lower()
                        or not (
                                "высшего" in univ_model.full_name.lower() or "высшего" in univ_model.type_name.lower())):
                    continue
                univ_models.append(suppl_univ_model)
                eduprogs = suppl.findall("EducationalPrograms/EducationalProgram")
                for eduprog in eduprogs:
                    prog_model = dm.EduProg(
                        id=eduprog.find("Id").text,
                        type_name=eduprog.find("TypeName").text,
                        edu_level_name=eduprog.find("EduLevelName").text,
                        programm_name=eduprog.find("ProgrammName").text,
                        programm_code=eduprog.find("ProgrammCode").text,
                        ugs_name=eduprog.find("UGSName").text,
                        ugs_code=eduprog.find("UGSCode").text,
                        edu_normative_period=eduprog.find("EduNormativePeriod").text,
                        qualification=eduprog.find("Qualification").text,
                        is_accredited=is_accredited_validator(eduprog.find("IsAccredited").text),
                        is_canceled=eduprog.find("IsCanceled").text,
                        is_suspended=eduprog.find("IsSuspended").text,
                        university_id=suppl_univ_model.id,
                    )
                    eduprog_models.append(prog_model)
        print("Статусы сертификатов:", cert_statuses)
        print("Статусы приложений:", suppl_statuses)
        return univ_models, eduprog_models

    univ_models, eduprog_models = await asyncio.to_thread(sync_xml_parse)
    actual_univs_id = set()
    actual_eduprogs_id = set()
    print(len(univ_models), len(eduprog_models))
    for univ_model in univ_models:
        try:
            await dbt.University.add(data=univ_model, custom=False)
            actual_univs_id.add(univ_model.id)
        except dbt.NotUnivError:
            pass
        except dbt.UniqueConstraintFailedError:
            await dbt.University.update(data=univ_model)
            actual_univs_id.add(univ_model.id)
    for prog_model in eduprog_models:
        try:
            await dbt.EduProg.add(data=prog_model, custom=False)
            actual_eduprogs_id.add(prog_model.id)
        except dbt.NotUnivError:
            pass
        except dbt.UniqueConstraintFailedError:
            await dbt.EduProg.update(data=prog_model)
            actual_eduprogs_id.add(prog_model.id)
    return actual_univs_id, actual_eduprogs_id


if __name__ == "__main__":
    asyncio.run(update_DB())
