import xml.etree.ElementTree as et
import db_tables as dbt
import data_models as dm
import datetime


def is_accredited_validator(value) -> int:
    value = dm.to_int_validator(value)
    return int(not value)


def xml_parse(filename: str):
    today = str(datetime.date.today())
    suppl_statuses = set()
    cert_statuses = set()
    actual_univs_id = set()
    actual_eduprogs_id = set()
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
        eduorg_id = eduorg.find("Id").text
        univ_model = dm.University(
            id=eduorg_id,
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
        try:
            dbt.University.add(data=univ_model, custom=False)
            actual_univs_id.add(eduorg_id)
        except dbt.NotUnivError:
            pass
        except dbt.UniqueConstraintFailedError:
            dbt.University.update(data=univ_model)
            actual_univs_id.add(eduorg_id)
        supplements = cert.findall("Supplements/Supplement")
        for suppl in supplements:
            suppl_status_name = suppl.find("StatusName").text
            suppl_statuses.add(suppl_status_name)
            if suppl_status_name != "Действующее":
                continue
            suppl_edu_org = suppl.find("ActualEducationOrganization")
            suppl_edu_org_id = suppl_edu_org.find("Id").text
            suppl_univ_model = dm.University(
                id=suppl_edu_org_id,
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
            try:
                dbt.University.add(data=suppl_univ_model, custom=False)
                actual_univs_id.add(suppl_edu_org_id)
            except dbt.NotUnivError:
                continue
            except dbt.UniqueConstraintFailedError:
                dbt.University.update(data=suppl_univ_model)
                actual_univs_id.add(suppl_edu_org_id)
            eduprogs = suppl.findall("EducationalPrograms/EducationalProgram")
            for eduprog in eduprogs:
                eduprog_id = eduprog.find("Id").text
                prog_model = dm.EduProg(
                    id=eduprog_id,
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
                    university_id=suppl_edu_org_id,
                )
                try:
                    dbt.EduProg.add(data=prog_model, custom=False)
                    actual_eduprogs_id.add(eduprog_id)
                except dbt.UniqueConstraintFailedError:
                    dbt.EduProg.update(data=prog_model)
                    actual_eduprogs_id.add(eduprog_id)
    print("Статусы сертификатов:", cert_statuses)
    print("Статусы приложений:", suppl_statuses)
    return actual_univs_id, actual_eduprogs_id
